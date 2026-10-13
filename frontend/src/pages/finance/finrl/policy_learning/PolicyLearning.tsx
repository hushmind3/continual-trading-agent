import {PolicyTrainingControls} from './PolicyTrainingControls';
import {CheckpointPanel} from './CheckpointPanel';
import {JobLog} from '../../../../ui/JobLog';
export function PolicyLearning(){return <div className="space-y-4"><PolicyTrainingControls/><JobLog/><CheckpointPanel/></div>}
