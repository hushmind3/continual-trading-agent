import type {ReactNode} from 'react';
import {Button,ErrorMessage} from './Primitives';

export function SettingsSection({title,description,actions,children}:{title:string;description?:string;actions?:ReactNode;children:ReactNode}) {
  return <section className="ui-settings-section"><header><div><h3>{title}</h3>{description&&<p>{description}</p>}</div>{actions&&<div className="ui-settings-section-actions">{actions}</div>}</header><div className="ui-settings-section-body">{children}</div></section>;
}
export function SettingsLoadState({error,retry}:{error:string;retry:()=>void}) {
  return <section className="ui-settings-load" aria-busy={!error}>{error?<><ErrorMessage message={error}/><Button onClick={retry}>다시 불러오기</Button></>:<p role="status">설정을 불러오는 중입니다…</p>}</section>;
}
