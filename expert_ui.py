"""Expert-only user interface; no custom financial dashboard or learning settings."""
import streamlit as st
from stockrl.expert_registry_native import ExpertRegistry

st.title('동결 Expert 등록·교체')
registry=ExpertRegistry();catalog=registry.catalog();items=catalog.get('experts',{})
st.caption('Actor·Critic·SAC·Optimizer·Loss·Replay·체결은 공식 구현을 사용합니다. 여기서는 동결 부품과 입력만 관리합니다.')
active=st.multiselect('사용할 Expert',list(items),default=catalog.get('active',[]),format_func=lambda key:items[key]['name'])
if st.button('선택 적용'):
    registry.select(active);st.success('Expert 선택을 저장했습니다. 다음 관측부터 읽습니다.')
with st.form('expert-registration'):
    source=st.text_input('Expert 패키지 파일의 전체 경로')
    slot=st.text_input('슬롯 이름')
    if st.form_submit_button('패키지 등록'):
        try:registry.register(source,slot);st.success('동결 Expert를 등록했습니다. 기존 중앙 모델은 승계하지 않습니다.')
        except (ValueError,OSError,RuntimeError) as error:st.error(str(error))
st.dataframe([{'슬롯':key,'모델':item['name'],'역할':'매매 판단' if item.get('role')=='action' else '시장 분석','상태':'선택됨' if key in active else '보관','파일':item['package']['file']} for key,item in items.items()],hide_index=True,use_container_width=True)
