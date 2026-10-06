'use strict';
const I18N=(()=>{
const UI={
tr:{short:{cp_gd:'CP-SAT → GD',pso:'PSO',ga:'GA',ts:'TS',ac:'AC',hs:'HS',heuristic:'Özgü sezgisel',ann:'Sinir ağı',sa:'SA'},names:{cp_gd:'CP-SAT → Great Deluge',pso:'Parçacık Sürü Optimizasyonu (PSO)',ga:'Genetik Algoritma (GA)',ts:'Tabu Arama (TS)',ac:'Karınca Kolonisi (AC)',hs:'Harmony Search (HS)',heuristic:'Probleme Özgü Sezgisel',ann:'Sinir Ağı (enerji modeli)',sa:'Benzetilmiş Tavlama (SA)'}},
en:{short:{cp_gd:'CP-SAT → GD',pso:'PSO',ga:'GA',ts:'TS',ac:'AC',hs:'HS',heuristic:'Heuristic',ann:'Neural net',sa:'SA'},names:{cp_gd:'CP-SAT → Great Deluge',pso:'Particle Swarm Optimization (PSO)',ga:'Genetic Algorithm (GA)',ts:'Tabu Search (TS)',ac:'Ant Colony (AC)',hs:'Harmony Search (HS)',heuristic:'Problem-specific heuristic',ann:'Neural network (energy model)',sa:'Simulated Annealing (SA)'}}};
let language='tr';
const L=(tr,en)=>language==='en'?en:tr;
function setLanguage(value){language=value==='en'?'en':'tr';}
return {UI,L,setLanguage};
})();
if(typeof module!=='undefined')module.exports=I18N;
