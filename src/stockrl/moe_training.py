"""Batched realized-horizon NAV learning through the public TorchRL objective.

Legacy behavior probabilities cannot be reconstructed: those rows train value.
"""
import json
import torch
from torch.nn import functional as F
from tensordict import TensorDict
from tensordict.nn import TensorDictModule
from torchrl.objectives import ClipPPOLoss
from .moe_policy import TorchRLActor
from .operating_rules import operating_rules
from .trading_moe import parameter_digest


def update_batch(model, optimizer, records, *, settings=None):
    rules = settings or operating_rules()
    device = next(model.controller.parameters()).device
    groups = {}
    for exp, snapshot, decision in records:
        if (exp.origin_model != 'trading_moe' or exp.source != 'paper_account_portfolio'
                or exp.portfolio_reward is None):
            raise ValueError('learner requires actual paper NAV outcomes')
        behavior = decision.get('behavior')
        usable = bool(behavior and behavior['stochastic'] and
                      behavior['schema'] == 'joint_categorical_dirichlet_v1' and
                      0 <= model.optimizer_updates - behavior['policy_version'] <= rules['max_policy_lag'])
        key = (tuple(snapshot['symbols']), json.dumps(behavior['layout'], sort_keys=True) if usable else None)
        groups.setdefault(key, []).append((exp, snapshot, decision, usable))
    if not groups:
        return None
    optimizer.zero_grad(set_to_none=True)
    before = parameter_digest(model.controller)
    losses = []; value_losses = []; clip_fractions = []; kl = []
    policy_rows = 0
    for rows in groups.values():
        evidence_rows = []; mask_rows = []; account_rows = []; q_rows = []
        for exp, snapshot, decision, _ in rows:
            evidence, mask = model.prepare(decision['raw_outputs'], snapshot['symbols'])
            evidence_rows.append(evidence); mask_rows.append(mask)
            q_rows.append(model.policy_q(decision['raw_outputs'], snapshot['symbols']))
            p = torch.as_tensor(exp.portfolio_state, dtype=torch.float32, device=device)
            a = torch.as_tensor(exp.account_state, dtype=torch.float32, device=device).expand(len(p), -1)
            account_rows.append(torch.cat([p, a], -1))
        evidence = {k: torch.cat([e[k] for e in evidence_rows]) for k in evidence_rows[0]}
        masks = {k: torch.cat([e[k] for e in mask_rows]) for k in mask_rows[0]}
        q = {k: torch.cat([e[k] for e in q_rows]) for k in q_rows[0]}
        output = model.controller(evidence, masks, torch.stack(account_rows), q)
        predicted = output['value'].mean(-1, keepdim=True)
        target = torch.tensor([[float(rules['training_reward_scale'])*float(e.portfolio_reward)]
                               for e, _, _, _ in rows], device=device)
        if rows[0][3]:
            behavior = [d['behavior'] for _, _, d, _ in rows]
            td = TensorDict(dict(logits=output['policy_logits'], scores=output['allocation_scores'],
                cash=output['cash_scores'], predicted=predicted, value_target=target,
                advantage=target-torch.tensor([[b['value']] for b in behavior], device=device),
                sample_log_prob=torch.tensor([b['log_prob'] for b in behavior], device=device),
                action=torch.tensor([b['action'] for b in behavior], device=device)), batch_size=[len(rows)])
            loss_module = ClipPPOLoss(TorchRLActor(behavior[0]['layout']),
                TensorDictModule(torch.nn.Identity(), ['predicted'], ['state_value']),
                functional=False, clip_epsilon=float(rules['policy_clip_epsilon']),
                entropy_bonus=False, critic_coeff=float(rules['value_loss_weight']),
                log_explained_variance=False, max_importance_ratio=float(rules['max_importance_ratio']))
            result = loss_module(td)
            objective = result['loss_objective'] + result['loss_critic']
            value_losses.append(result['loss_critic'].detach())
            clip_fractions.append(float(result['clip_fraction']))
            kl.append(float(result['kl_approx']))
            policy_rows += len(rows)
        else:
            value = F.smooth_l1_loss(predicted, target)
            objective = float(rules['value_loss_weight'])*value
            value_losses.append(value.detach())
        gates = output['router_probabilities']
        entropy = -(gates*gates.clamp_min(1e-8).log()).sum(-1).mean()
        losses.append((objective-float(rules['router_entropy_weight'])*entropy)*len(rows)/len(records))
    loss = sum(losses)
    if not torch.isfinite(loss):
        raise ValueError('nonfinite training loss; replay has not been acknowledged')
    loss.backward()
    parameters = [p for group in optimizer.param_groups for p in group['params']]
    norm = torch.nn.utils.clip_grad_norm_(parameters, float(rules['gradient_clip_norm']), error_if_nonfinite=True)
    optimizer.step(); model.optimizer_updates += 1
    after = parameter_digest(model.controller)
    if after == before:
        raise ValueError('controller update did not change weights')
    return dict(loss=float(loss.detach()), value_loss=float(torch.stack(value_losses).mean()),
        reward_points=sum(float(e.portfolio_reward)*rules['training_reward_scale'] for e,_,_ in records)/len(records),
        contexts=len(records), policy_contexts=policy_rows, value_only_contexts=len(records)-policy_rows,
        gradient_norm=float(norm), clip_fraction=sum(clip_fractions)/max(1,len(clip_fractions)),
        approximate_kl=sum(kl)/max(1,len(kl)), controller_before=before, controller_after=after,
        expert_versions_unchanged=True, optimizer_updates=model.optimizer_updates)
