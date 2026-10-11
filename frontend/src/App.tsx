import {useEffect,useState} from 'react';
import {Shell,Page,route} from './shell/Shell';
export {route} from './shell/Shell';
export default function App(){
  const [hash,setHash]=useState(()=>location.hash);const active=route(hash);
  useEffect(()=>{const changed=()=>setHash(location.hash);window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[]);
  return <Shell active={active}><Page active={active}/></Shell>;
}
