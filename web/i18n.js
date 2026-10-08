'use strict';
const I18N=(()=>{
const UI={
tr:{short:{cp_gd:'CP-SAT → GD',mip:'MIP / CBC',ilp:'ILP / CP-SAT',goal:'Hedef / CBC'},names:{cp_gd:'Makale: CP-SAT → Great Deluge',mip:'MIP (CBC)',ilp:'ILP (CP-SAT)',goal:'Hedef Programlama (CBC)'}},
en:{short:{cp_gd:'CP-SAT → GD',mip:'MIP / CBC',ilp:'ILP / CP-SAT',goal:'Goal / CBC'},names:{cp_gd:'Paper: CP-SAT → Great Deluge',mip:'MIP (CBC)',ilp:'ILP (CP-SAT)',goal:'Goal Programming (CBC)'}}};
let language='tr';
const L=(tr,en)=>language==='en'?en:tr;
function setLanguage(value){language=value==='en'?'en':'tr';}
return {UI,L,setLanguage};
})();
if(typeof module!=='undefined')module.exports=I18N;
