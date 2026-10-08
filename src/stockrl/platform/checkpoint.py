"""Small policy versions with checksums, atomic publication and bounded rollback."""
import hashlib
import os
import time
from pathlib import Path
from ..state_io import atomic_json, read_json


class Checkpoints:
    def __init__(self, root: Path, retain=5):
        self.root, self.retain = Path(root), retain
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, actor, critic, optimizer, version, expert_ids, applied_ids=(), *, optimizer_steps=0,optimization_generation=None,publish=True):
        import torch
        name = f"policy-{version:08d}-{time.time_ns()}.pt"
        path = self.root / name
        temp = path.with_suffix(".tmp")
        state = {"format": "finrlx-portfolio-ppo-v1", "expert_ids": expert_ids, "version": version,
                 "model_spec":actor.model_spec,
                 "actor": actor.state_dict(), "critic": critic.state_dict(),
                 "optimizer": optimizer.state_dict() if optimizer else None, "applied_ids": list(applied_ids),
                 "torch_rng": torch.get_rng_state(), "optimizer_steps":optimizer_steps,
                 "optimization_generation":version if optimization_generation is None else optimization_generation}
        with temp.open("wb") as stream:
            torch.save(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        manifest = {"file": name, "version": version, "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "time": time.time()}
        atomic_json(manifest, path.with_suffix(".json"))
        if publish:
            self.mirror(state)
            atomic_json(manifest, self.root / "current.json")
        revisions = sorted(self.root.glob("policy-*.json"), key=lambda p:p.stat().st_mtime, reverse=True)
        for record in revisions[self.retain:]:
            record.with_suffix(".pt").unlink(missing_ok=True)
            record.unlink()
        return manifest

    def mirror(self,state):
        """Champion carries the current learned decision state, never duplicated Expert bodies."""
        from .expert_packages import HEADER_FORMAT
        import torch
        spec=state['model_spec']
        if spec.get('source_format')!=HEADER_FORMAT:return
        path=Path(spec['source_model'])
        if not path.is_file():raise ValueError('Champion 구성 파일이 없습니다.')
        header=torch.load(path,map_location='cpu',weights_only=True)
        if header.get('format')!=HEADER_FORMAT or header['expert_packages']!=spec['expert_packages']:
            raise ValueError('현재 Champion과 정책의 Expert 버전이 다릅니다.')
        header['learned_policy']=state
        from .model_composition import atomic_torch_save
        temporary=atomic_torch_save(header,path);temporary.replace(path)

    def publish(self,manifest):
        import torch
        state=torch.load(self.root/manifest['file'],map_location='cpu',weights_only=True)
        self.mirror(state);atomic_json(manifest,self.root/'current.json')

    def load(self, recover=True):
        import torch
        manifest = read_json(self.root / "current.json")
        if not manifest:
            return None, None
        candidates=[manifest]+([r for r in self.revisions() if r.get('file')!=manifest.get('file')] if recover else [])
        for record in candidates:
            try:
                path=self.root/Path(record['file']).name
                if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
                    continue
                state=torch.load(path,map_location='cpu',weights_only=True)
                if state.get('format')!='finrlx-portfolio-ppo-v1':
                    continue
                if record is not manifest:
                    record={**record,'recovered_from':manifest.get('file')}
                    atomic_json(record,self.root/'current.json')
                return state,record
            except (OSError,KeyError,RuntimeError):
                continue
        raise ValueError('정상적인 정책 버전이 없습니다. 원본 MoE로 초기화하거나 정상 버전을 복원하세요.')

    def revisions(self):
        return [read_json(p) for p in sorted(self.root.glob("policy-*.json"), key=lambda p:p.stat().st_mtime, reverse=True)]

    def rollback(self, name):
        if Path(name).name != name or not name.startswith("policy-"):
            raise ValueError("저장된 정책 버전을 선택하세요.")
        manifest = read_json(self.root / Path(name).with_suffix(".json"))
        if not manifest:
            raise ValueError("해당 정책 버전이 없습니다.")
        path = self.root / manifest["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("해당 버전의 checksum이 맞지 않습니다.")
        self.publish(manifest)
        return manifest
