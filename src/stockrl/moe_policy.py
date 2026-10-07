"""A single behavior law shared by inference and TorchRL training.

The joint action contains categorical decisions and one simplex per currency.
Unquoted/uncovered holdings are fixed, never sampled or assigned likelihood.
"""
import torch
from torch import nn
from torch.distributions import Categorical, Dirichlet, Distribution
from torch.nn.functional import softplus


def policy_layout(snapshot, coverage):
    symbols = snapshot['symbols']
    tradable = set(snapshot.get('tradable_symbols', symbols))
    active = [i for i, s in enumerate(symbols) if coverage[i] and s in tradable]
    groups = []
    for currency in sorted(set(snapshot['currencies'].values())):
        indices = [i for i in active if snapshot['currencies'][symbols[i]] == currency]
        held = sum(snapshot['current_weights'][s] for i, s in enumerate(symbols)
                   if snapshot['currencies'][s] == currency and i not in indices)
        remaining = max(0., 1. - held)
        if indices and remaining > 1e-8:
            groups.append(dict(currency=currency, indices=indices, budget=remaining))
    active = [i for group in groups for i in group['indices']]
    return dict(active=active, groups=groups, symbols=list(symbols))


class JointPolicy(Distribution):
    """Product of masked categorical actions and independent currency Dirichlets."""
    arg_constraints = {}

    def __init__(self, logits, scores, cash, layout):
        self.layout = layout
        self.categorical = Categorical(logits=logits[..., layout['active'], :])
        self.allocations = [Dirichlet(softplus(torch.cat(
            [scores[..., group['indices']], cash], -1)) + 1.) for group in layout['groups']]
        size = len(layout['active']) + sum(len(g['indices']) + 1 for g in layout['groups'])
        super().__init__(logits.shape[:-2], torch.Size([size]), validate_args=False)

    def sample(self, sample_shape=torch.Size()):
        return torch.cat([self.categorical.sample(sample_shape).float(),
                          *[d.sample(sample_shape) for d in self.allocations]], -1)

    @property
    def mode(self):
        return torch.cat([self.categorical.logits.argmax(-1).float(),
                          *[(d.concentration-1)/(d.concentration-1).sum(-1, keepdim=True)
                            for d in self.allocations]], -1)

    def log_prob(self, value):
        n = len(self.layout['active'])
        result = self.categorical.log_prob(value[..., :n].long()).sum(-1)
        for distribution in self.allocations:
            end = n + distribution.event_shape[0]
            result = result + distribution.log_prob(value[..., n:end])
            n = end
        return result

    def entropy(self):
        return self.categorical.entropy().sum(-1) + sum(d.entropy() for d in self.allocations)


def select_action(output, snapshot, trading, *, explore, version):
    layout = policy_layout(snapshot, output['coverage'][0].tolist())
    if not layout['active']:
        trading['paper_executable'] = False
        return None
    distribution = JointPolicy(output['policy_logits'], output['allocation_scores'], output['cash_scores'], layout)
    action = (distribution.sample() if explore else distribution.mode).detach()
    actions = {s: 'HOLD' for s in snapshot['symbols']}
    weights = dict(snapshot['current_weights'])
    n = len(layout['active'])
    for i, index in enumerate(layout['active']):
        actions[snapshot['symbols'][index]] = ('SELL', 'HOLD', 'BUY')[int(action[0, i])]
    cash = {}
    for group in layout['groups']:
        for j, index in enumerate(group['indices']):
            weights[snapshot['symbols'][index]] = float(action[0, n+j]) * group['budget']
        n += len(group['indices'])
        cash[group['currency']] = float(action[0, n]) * group['budget']
        n += 1
    for currency in set(snapshot['currencies'].values()) - set(cash):
        cash[currency] = max(0., 1.-sum(v for s,v in weights.items() if snapshot['currencies'][s] == currency))
    trading.update(actions=actions, target_weights=weights, cash_weights_by_currency=cash,
                   selected_symbols=[s for s in weights if weights[s] > 1e-6])
    return dict(schema='joint_categorical_dirichlet_v1', layout=layout, action=action[0].cpu().tolist(),
                log_prob=float(distribution.log_prob(action)[0]), value=float(output['value'].mean()),
                policy_version=version, stochastic=bool(explore))


class TorchRLActor(nn.Module):
    """Public get_dist protocol; native Expert bodies are outside this actor."""
    in_keys = ['logits', 'scores', 'cash']
    out_keys = ['action', 'sample_log_prob']
    log_prob_keys = ['sample_log_prob']
    dist_sample_keys = ['action']

    def __init__(self, layout):
        super().__init__()
        self.layout = layout

    def get_dist(self, tensordict):
        return JointPolicy(tensordict['logits'], tensordict['scores'], tensordict['cash'], self.layout)
