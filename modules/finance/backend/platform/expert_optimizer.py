"""Existing Frozen Expert comparison/selection functions restored from f153957."""
import json,hashlib
import numpy as np

def best_precision(reports,current,goal,ram_total,vram_total,quantization_first=False):
    def pressure(row):
        metrics=row['measurement']['metrics']
        return max((metrics.get('resident_bytes') or row['bytes'])/max(vram_total,1),1e-6) if goal=='memory' else max(metrics.get('peak_ram_bytes',0)/max(ram_total,1),metrics.get('peak_vram_bytes',0)/max(vram_total,1),1e-6)
    reference=next(r for r in reports if r['id']==current)
    seconds=max(reference['measurement']['warm_median_seconds'],1e-6);memory=pressure(reference)
    for row in reports:
        latency=row['measurement']['warm_median_seconds']/seconds;ram=pressure(row)/memory
        row['score']=latency if goal=='speed' else ram if goal=='memory' else .6*latency+.4*ram
        row['eligible']=row['passed']
    eligible=[r for r in reports if r['eligible']]
    if quantization_first:
        compressed=[r for r in eligible if r['precision'].lower().startswith(('nf4','int4','int8','gguf'))]
        if compressed:eligible=compressed
    if not eligible:
        # Preserve quality even when returning to FP32 costs more time than a rejected current variant.
        eligible=[r for r in reports if r['passed']]
    chosen=min(eligible,key=lambda r:(r['score'],r['bytes']))
    if not quantization_first and reference['passed'] and chosen['score']>.95:chosen=reference
    for row in reports:
        row['decision']='selected' if row is chosen else 'rejected' if not row['eligible'] else 'not_selected'
        if row is chosen:
            row['reason']=('기존 버전이 출력 기준을 넘어서 통과한 버전으로 복귀 · 정확도를 우선' if not reference['passed'] else
                '허용 기준을 통과한 최적 후보' if row['id']!=current else '5% 이상 개선되는 적격 후보가 없어 현재 버전 유지')
        elif not row['passed']:row['reason']=row.get('detail','출력 허용 기준 초과')
        elif not row['eligible']:row['reason']=f"현재 버전 대비 추론 시간이 {'50' if goal=='memory' else '15'}% 넘게 증가해 제외"
        elif row['score']>.95 and chosen is reference:row['reason']='현재 버전 대비 목표 점수 개선이 5% 미만'
        else:row['reason']='선택된 버전보다 목표 점수가 높아 미선택 · 낮을수록 유리'
    return chosen

def measurement_summary(value):
    return {key:v for key,v in value.items() if key not in ('packet','packets','outputs','weight_files')}
