import unittest
from stockrl.platform.progress_status import ProgressTracker


def snapshot(now=100):
    workers={k:dict(pid=i,created_at=1,alive=True,requested=True,heartbeat=now,status='waiting') for i,k in enumerate(('feed','experts','agent','learner'),1)}
    workers['feed'].update(new_rows_total=0,poll_cycles_total=1)
    workers['agent'].update(decision_batches_total=0,market_batches_total=0,message='새로운 완료 시세 대기')
    workers['learner']['optimizer_steps']=330
    return dict(time=now,workers=workers,experts=[dict(id='a',enabled=True,inference_count=10,new_input_count=1,last_completed_at=90,last_as_of='2026-10-08')],
        settings={'resources':{'inference_timeout_seconds':180}},training={'label':'경험 대기','detail':'2/32개'},last_learning={'time':50})


class ProgressTests(unittest.TestCase):
    def test_alive_and_polling_are_not_proof_of_new_market_data_or_learning(self):
        tracker=ProgressTracker();s=snapshot();tracker.snapshot(s)
        s['time']=120;s['workers']['feed']['poll_cycles_total']=3
        value=tracker.snapshot(s)
        self.assertTrue(value['feed']['service_alive']);self.assertEqual(value['feed']['changes']['new_bars'],0)
        self.assertEqual(value['feed']['changes']['polls'],2);self.assertEqual(value['feed']['code'],'waiting')
        self.assertEqual(value['learner']['changes']['updates'],0);self.assertEqual(value['learner']['last_completed_at'],50)

    def test_repeat_analysis_is_separate_from_new_input(self):
        tracker=ProgressTracker();s=snapshot();tracker.snapshot(s);s['time']=110;s['experts'][0]['inference_count']=12
        value=tracker.snapshot(s)['experts']
        self.assertEqual(value['changes'],{'inferences':2,'new_inputs':0});self.assertEqual(value['code'],'progress')

    def test_restart_and_gaps_reset_the_observation_without_fake_spikes(self):
        tracker=ProgressTracker();s=snapshot();tracker.snapshot(s)
        s['time']=110;s['workers']['learner']['pid']=99;s['workers']['learner']['optimizer_steps']=500
        value=tracker.snapshot(s)['learner'];self.assertEqual(value['changes']['updates'],0)
        s['time']=200;s['workers']['learner']['optimizer_steps']=510
        self.assertEqual(tracker.snapshot(s)['learner']['changes']['updates'],0)

    def test_actual_new_bars_and_optimizer_steps_are_visible(self):
        tracker=ProgressTracker();s=snapshot();tracker.snapshot(s);s['time']=110
        s['workers']['feed']['new_rows_total']=5;s['workers']['learner']['optimizer_steps']=334
        values=tracker.snapshot(s)
        self.assertEqual(values['feed']['changes']['new_bars'],5);self.assertEqual(values['learner']['changes']['updates'],4)
        self.assertEqual(values['learner']['code'],'progress')


if __name__=='__main__':unittest.main()
