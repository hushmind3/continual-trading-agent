const extension=/\.(md|txt|json|csv|log|py|tsx?|jsx?|yaml|yml|toml|html|css)(?::\d+(?::\d+)?)?(?:#L?\d+(?:-L?\d+)?)?$/i;
export function documentPath(value:string){
 const path=value.trim();
 if(/[\r\n]/.test(path)||!extension.test(path))return;
 if(path.startsWith('/')&&!/^\/(?:[a-z]:[\\/]|[a-z]\/)/i.test(path))return;
 if(/^[a-z][a-z0-9+.-]*:/i.test(path)&&!/^file:/i.test(path)&&!/^[a-z]:[\\/]/i.test(path))return;
 return path;
}
export function relativeDocumentPath(value:string,base:string){
 const path=documentPath(value);
 if(!path)return;
 if(/^(?:file:|[a-z]:[\\/]|[\\/])/i.test(path))return path;
 return base.replaceAll('\\','/').replace(/[^/]+$/,'')+path;
}
