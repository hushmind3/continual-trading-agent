import {FileText, Image, X} from 'lucide-react';
import {IconButton} from './Primitives';

export interface AttachedFile {name: string; path: string; bytes: number}
const fileSize = (bytes: number) => bytes < 1024 ? `${bytes} B`
  : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

export function FileChips({files, remove}: {files: AttachedFile[]; remove: (path: string) => void}) {
  if (!files.length) return null;
  return <div className="ui-file-chips" aria-label="첨부 파일">
    {files.map(file => <div className="ui-file-chip" key={file.path}>
      {/\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name) ? <Image size={18}/> : <FileText size={18}/>}
      <div><strong title={file.name}>{file.name}</strong><small>{fileSize(file.bytes)} · 첨부됨</small></div>
      <IconButton type="button" variant="ghost" aria-label={file.name + ' 첨부 취소'} onClick={() => remove(file.path)}><X size={14}/></IconButton>
    </div>)}
  </div>;
}
