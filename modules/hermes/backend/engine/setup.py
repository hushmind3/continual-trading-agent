"""Install the complete official locked runtime, never a hand-maintained subset."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    engine=Path(__file__).resolve().parent
    sys.path.insert(0,str(engine))
    from prepare import prepare
    prepare(engine)
    root=engine.parents[3]
    env=dict(os.environ)
    env.pop('PYTHONPATH',None)
    env['HERMES_HOME']=str(root/'runtime/ai_agent/Hermes')
    env['HERMES_RUNTIME_DIR']=str(root/'runtime/shared/engines/hermes-pm')
    subprocess.run([sys.executable,'-m','pm.cli','install'],cwd=engine/'upstream',env=env,check=True)
    result=subprocess.run([sys.executable,'-m','pm.cli','env'],cwd=engine/'upstream',env=env,capture_output=True,text=True,check=True)
    managed=json.loads(result.stdout)
    managed['PATH']=os.pathsep.join((managed['PATH'],env.get('PATH',os.defpath)))
    env.update(managed)
    os.environ.update(managed)
    sys.path.insert(0,str(root/'backend'))
    from platform_native import npm_command
    subprocess.run([*npm_command(), '--prefix',str(engine/'upstream/web'),'install','--package-lock=false','--no-audit','--no-fund'],cwd=root,env=env,check=True)


if __name__=='__main__':main()
