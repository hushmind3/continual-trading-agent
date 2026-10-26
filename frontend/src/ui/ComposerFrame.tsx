import type {DragEventHandler, FormEventHandler, ReactNode} from 'react';

interface Props {
  children: ReactNode;
  toolbar: ReactNode;
  attachments?: ReactNode;
  options?: ReactNode;
  dragging?: boolean;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onDragOver?: DragEventHandler<HTMLFormElement>;
  onDragLeave?: DragEventHandler<HTMLFormElement>;
  onDrop?: DragEventHandler<HTMLFormElement>;
}

/** Full-width writing surface with a separate, stable action row. */
export function ComposerFrame({children, toolbar, attachments, options, dragging, ...events}: Props) {
  return <form {...events} className={'hermes-composer' + (dragging ? ' is-dragging' : '')}>
    {attachments}
    <div className="ui-composer-editor relative">{children}</div>
    <div className="ui-composer-toolbar">{toolbar}</div>
    {options}
    {dragging && <div className="ui-composer-drop-hint">여기에 파일을 놓아 첨부하세요</div>}
  </form>;
}
