define("nbextensions/ipyflow/index",[],(()=>(()=>{var e={760:(e,n,o)=>{"use strict";o.r(n),o.d(n,{default:()=>a});var t=o(15),l=o.n(t),r=o(645),c=o.n(r)()(l());c.push([e.id,":root {\n  --waiting-color: rgb(254,0,82);\n  --ready-making-color: rgb(0,197,158);\n}\n\n.cell.code_cell .out_prompt_overlay::before {\n  position: absolute;\n  display: block;\n  top: 3px;\n  left: -6px;\n  width: 5px;\n  height: calc(100% + 2px);\n  content: '';\n}\n\n.cell.code_cell .input_prompt::before {\n  position: absolute;\n  display: block;\n  top: -1px;\n  left: -1px;\n  width: 5px;\n  height: calc(100% + 2px);\n  content: '';\n}\n\n.cell.code_cell.waiting-cell .input_prompt::before {\n  border: 1px solid var(--waiting-color);\n}\n\n.cell.code_cell.waiting-cell.selected .input_prompt::before, .waiting-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.waiting-cell .input_prompt:hover::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.linked-waiting .input_prompt::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.linked-ready .out_prompt_overlay::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-making-cell .input_prompt::before {\n  border: 1px solid var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-cell.selected .input_prompt::before, .cell.code_cell.ready-making-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-cell .input_prompt:hover::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.linked-ready-making .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n/* put input / output cells later since they should take precedence */\n\n.cell.code_cell.ready-cell .out_prompt_overlay::before {\n  border: 1px solid var(--waiting-color);\n}\n\n.cell.code_cell.ready-cell.selected .out_prompt_overlay::before, .cell.code_cell.ready-cell.jupyter-soft-selected .out_prompt_overlay::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-cell .out_prompt_overlay:hover::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-making-input-cell .input_prompt::before {\n  border: 1px solid var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-input-cell.selected .input_prompt::before, .cell.code_cell.ready-making-input-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-input-cell .input_prompt:hover::before {\n  background-color: var(--ready-making-color);\n}\n","",{version:3,sources:["webpack://./style/index.css"],names:[],mappings:"AAAA;EACE,8BAA8B;EAC9B,oCAAoC;AACtC;;AAEA;EACE,kBAAkB;EAClB,cAAc;EACd,QAAQ;EACR,UAAU;EACV,UAAU;EACV,wBAAwB;EACxB,WAAW;AACb;;AAEA;EACE,kBAAkB;EAClB,cAAc;EACd,SAAS;EACT,UAAU;EACV,UAAU;EACV,wBAAwB;EACxB,WAAW;AACb;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,2CAA2C;AAC7C;;AAEA;EACE,2CAA2C;AAC7C;;AAEA;EACE,2CAA2C;AAC7C;;AAEA;EACE,2CAA2C;AAC7C;;AAEA,qEAAqE;;AAErE;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,sCAAsC;AACxC;;AAEA;EACE,2CAA2C;AAC7C;;AAEA;EACE,2CAA2C;AAC7C;;AAEA;EACE,2CAA2C;AAC7C",sourcesContent:[":root {\n  --waiting-color: rgb(254,0,82);\n  --ready-making-color: rgb(0,197,158);\n}\n\n.cell.code_cell .out_prompt_overlay::before {\n  position: absolute;\n  display: block;\n  top: 3px;\n  left: -6px;\n  width: 5px;\n  height: calc(100% + 2px);\n  content: '';\n}\n\n.cell.code_cell .input_prompt::before {\n  position: absolute;\n  display: block;\n  top: -1px;\n  left: -1px;\n  width: 5px;\n  height: calc(100% + 2px);\n  content: '';\n}\n\n.cell.code_cell.waiting-cell .input_prompt::before {\n  border: 1px solid var(--waiting-color);\n}\n\n.cell.code_cell.waiting-cell.selected .input_prompt::before, .waiting-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.waiting-cell .input_prompt:hover::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.linked-waiting .input_prompt::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.linked-ready .out_prompt_overlay::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-making-cell .input_prompt::before {\n  border: 1px solid var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-cell.selected .input_prompt::before, .cell.code_cell.ready-making-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-cell .input_prompt:hover::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.linked-ready-making .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n/* put input / output cells later since they should take precedence */\n\n.cell.code_cell.ready-cell .out_prompt_overlay::before {\n  border: 1px solid var(--waiting-color);\n}\n\n.cell.code_cell.ready-cell.selected .out_prompt_overlay::before, .cell.code_cell.ready-cell.jupyter-soft-selected .out_prompt_overlay::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-cell .out_prompt_overlay:hover::before {\n  background-color: var(--waiting-color);\n}\n\n.cell.code_cell.ready-making-input-cell .input_prompt::before {\n  border: 1px solid var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-input-cell.selected .input_prompt::before, .cell.code_cell.ready-making-input-cell.jupyter-soft-selected .input_prompt::before {\n  background-color: var(--ready-making-color);\n}\n\n.cell.code_cell.ready-making-input-cell .input_prompt:hover::before {\n  background-color: var(--ready-making-color);\n}\n"],sourceRoot:""}]);const a=c},645:e=>{"use strict";e.exports=function(e){var n=[];return n.toString=function(){return this.map((function(n){var o=e(n);return n[2]?"@media ".concat(n[2]," {").concat(o,"}"):o})).join("")},n.i=function(e,o,t){"string"==typeof e&&(e=[[null,e,""]]);var l={};if(t)for(var r=0;r<this.length;r++){var c=this[r][0];null!=c&&(l[c]=!0)}for(var a=0;a<e.length;a++){var i=[].concat(e[a]);t&&l[i[0]]||(o&&(i[2]?i[2]="".concat(o," and ").concat(i[2]):i[2]=o),n.push(i))}},n}},15:e=>{"use strict";function n(e,n){(null==n||n>e.length)&&(n=e.length);for(var o=0,t=new Array(n);o<n;o++)t[o]=e[o];return t}e.exports=function(e){var o,t,l=(t=4,function(e){if(Array.isArray(e))return e}(o=e)||function(e,n){var o=e&&("undefined"!=typeof Symbol&&e[Symbol.iterator]||e["@@iterator"]);if(null!=o){var t,l,r=[],c=!0,a=!1;try{for(o=o.call(e);!(c=(t=o.next()).done)&&(r.push(t.value),!n||r.length!==n);c=!0);}catch(e){a=!0,l=e}finally{try{c||null==o.return||o.return()}finally{if(a)throw l}}return r}}(o,t)||function(e,o){if(e){if("string"==typeof e)return n(e,o);var t=Object.prototype.toString.call(e).slice(8,-1);return"Object"===t&&e.constructor&&(t=e.constructor.name),"Map"===t||"Set"===t?Array.from(e):"Arguments"===t||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t)?n(e,o):void 0}}(o,t)||function(){throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")}()),r=l[1],c=l[3];if(!c)return r;if("function"==typeof btoa){var a=btoa(unescape(encodeURIComponent(JSON.stringify(c)))),i="sourceMappingURL=data:application/json;charset=utf-8;base64,".concat(a),d="/*# ".concat(i," */"),s=c.sources.map((function(e){return"/*# sourceURL=".concat(c.sourceRoot||"").concat(e," */")}));return[r].concat(s).concat([d]).join("\n")}return[r].join("\n")}},549:(e,n,o)=>{var t=o(379),l=o(760);"string"==typeof(l=l.__esModule?l.default:l)&&(l=[[e.id,l,""]]);t(l,{insert:"head",singleton:!1}),e.exports=l.locals||{}},379:(e,n,o)=>{"use strict";var t,l=function(){var e={};return function(n){if(void 0===e[n]){var o=document.querySelector(n);if(window.HTMLIFrameElement&&o instanceof window.HTMLIFrameElement)try{o=o.contentDocument.head}catch(e){o=null}e[n]=o}return e[n]}}(),r=[];function c(e){for(var n=-1,o=0;o<r.length;o++)if(r[o].identifier===e){n=o;break}return n}function a(e,n){for(var o={},t=[],l=0;l<e.length;l++){var a=e[l],i=n.base?a[0]+n.base:a[0],d=o[i]||0,s="".concat(i," ").concat(d);o[i]=d+1;var u=c(s),p={css:a[1],media:a[2],sourceMap:a[3]};-1!==u?(r[u].references++,r[u].updater(p)):r.push({identifier:s,updater:f(p,n),references:1}),t.push(s)}return t}function i(e){var n=document.createElement("style"),t=e.attributes||{};if(void 0===t.nonce){var r=o.nc;r&&(t.nonce=r)}if(Object.keys(t).forEach((function(e){n.setAttribute(e,t[e])})),"function"==typeof e.insert)e.insert(n);else{var c=l(e.insert||"head");if(!c)throw new Error("Couldn't find a style target. This probably means that the value for the 'insert' parameter is invalid.");c.appendChild(n)}return n}var d,s=(d=[],function(e,n){return d[e]=n,d.filter(Boolean).join("\n")});function u(e,n,o,t){var l=o?"":t.media?"@media ".concat(t.media," {").concat(t.css,"}"):t.css;if(e.styleSheet)e.styleSheet.cssText=s(n,l);else{var r=document.createTextNode(l),c=e.childNodes;c[n]&&e.removeChild(c[n]),c.length?e.insertBefore(r,c[n]):e.appendChild(r)}}function p(e,n,o){var t=o.css,l=o.media,r=o.sourceMap;if(l?e.setAttribute("media",l):e.removeAttribute("media"),r&&"undefined"!=typeof btoa&&(t+="\n/*# sourceMappingURL=data:application/json;base64,".concat(btoa(unescape(encodeURIComponent(JSON.stringify(r))))," */")),e.styleSheet)e.styleSheet.cssText=t;else{for(;e.firstChild;)e.removeChild(e.firstChild);e.appendChild(document.createTextNode(t))}}var A=null,m=0;function f(e,n){var o,t,l;if(n.singleton){var r=m++;o=A||(A=i(n)),t=u.bind(null,o,r,!1),l=u.bind(null,o,r,!0)}else o=i(n),t=p.bind(null,o,n),l=function(){!function(e){if(null===e.parentNode)return!1;e.parentNode.removeChild(e)}(o)};return t(e),function(n){if(n){if(n.css===e.css&&n.media===e.media&&n.sourceMap===e.sourceMap)return;t(e=n)}else l()}}e.exports=function(e,n){(n=n||{}).singleton||"boolean"==typeof n.singleton||(n.singleton=(void 0===t&&(t=Boolean(window&&document&&document.all&&!window.atob)),t));var o=a(e=e||[],n);return function(e){if(e=e||[],"[object Array]"===Object.prototype.toString.call(e)){for(var t=0;t<o.length;t++){var l=c(o[t]);r[l].references--}for(var i=a(e,n),d=0;d<o.length;d++){var s=c(o[d]);0===r[s].references&&(r[s].updater(),r.splice(s,1))}o=i}}}}},n={};function o(t){var l=n[t];if(void 0!==l)return l.exports;var r=n[t]={id:t,exports:{}};return e[t](r,r.exports,o),r.exports}o.n=e=>{var n=e&&e.__esModule?()=>e.default:()=>e;return o.d(n,{a:n}),n},o.d=(e,n)=>{for(var t in n)o.o(n,t)&&!o.o(e,t)&&Object.defineProperty(e,t,{enumerable:!0,get:n[t]})},o.o=(e,n)=>Object.prototype.hasOwnProperty.call(e,n),o.r=e=>{"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},o.nc=void 0;var t={};return(()=>{"use strict";o.r(t),o(549);const e="waiting-cell",n="ready-cell",l="ready-making-cell",r="ready-making-input-cell",c="linked-waiting",a="linked-ready",i="linked-ready-making",d=new Event("cleanup"),s=e=>null===e||null===e.firstElementChild||null===e.firstElementChild.firstElementChild?null:e.firstElementChild.firstElementChild.firstElementChild,u=e=>null===e||null===e.children.item(1)?null:e.children.item(1).firstElementChild,p=(e,n,o)=>{const t=()=>{e.removeEventListener(n,o),e.removeEventListener("cleanup",t)};e.addEventListener(n,o),e.addEventListener("cleanup",t)},A=(e,n,o,t,l)=>{null!==e&&p(e,o,(()=>{n.classList[t](l)}))},m=e=>{A(s(e),e,"mouseover","add",a),A(s(e),e,"mouseout","remove",a),A(u(e),e,"mouseover","add",i),A(u(e),e,"mouseout","remove",i)},f=(e,n,o,t,l,r)=>{const c=()=>{for(const e of n)o[e].classList[l](r)};e.addEventListener(t,c),p(e,t,c)},v=o=>{o.notebook.get_cells().forEach(((o,t)=>{o.element[0].classList.remove(e),o.element[0].classList.remove(l),o.element[0].classList.remove(n),o.element[0].classList.remove(r),o.element[0].classList.remove(c),o.element[0].classList.remove(a),o.element[0].classList.remove(i);const p=s(o.element[0]);null!==p&&p.dispatchEvent(d);const A=u(o.element[0]);null!==A&&A.dispatchEvent(d)}))},b=e=>{const n={};return e.notebook.get_cells().forEach(((e,o)=>{"code"===e.cell_type&&(n[e.cell_id]={index:o,content:e.get_text(),type:e.cell_type})})),n};require(["base/js/namespace"],(function(o){o.notebook.events.on("kernel_ready.Kernel",(()=>{const t=(o=>{const t=o.notebook.kernel.comm_manager.new_comm("ipyflow",{exec_schedule:"liveness_based"}),d=(e,l)=>{l.cell.notebook===o.notebook&&(l.cell.element[0].classList.remove(n),l.cell.element[0].classList.remove(r),t.send({type:"compute_exec_schedule",executed_cell_id:l.cell.cell_id,cell_metadata_by_id:b(o)}))},p=(e,n)=>{let l=null,r=0;o.notebook.get_cells().forEach((e=>{n.cell.cell_id===e.cell_id&&(l=r),r+=1})),t.send({type:"change_active_cell",active_cell_id:n.cell.cell_id,active_cell_order_idx:l})};return t.on_msg((t=>{if("establish"==t.content.data.type)o.notebook.events.on("execute.CodeCell",d),o.notebook.events.on("select.Cell",p);else if("compute_exec_schedule"===t.content.data.type){v(o);const d=t.content.data.waiting_cells,p=t.content.data.ready_cells,A=t.content.data.waiter_links,b=t.content.data.ready_maker_links,_={};o.notebook.get_cells().forEach((e=>{_[e.cell_id]=e.element[0]}));for(const[o,t]of Object.entries(_))d.indexOf(o)>-1?(t.classList.add(e),t.classList.add(n),t.classList.remove(r)):p.indexOf(o)>-1&&(t.classList.add(r),t.classList.add(n),m(t)),A.hasOwnProperty(o)&&(f(s(t),A[o],_,"mouseover","add",i),f(u(t),A[o],_,"mouseover","add",i),f(s(t),A[o],_,"mouseout","remove",i),f(u(t),A[o],_,"mouseout","remove",i)),b.hasOwnProperty(o)&&(t.classList.add(l),t.classList.add(n),m(t),f(s(t),b[o],_,"mouseover","add",c),f(s(t),b[o],_,"mouseover","add",a),f(s(t),b[o],_,"mouseout","remove",c),f(s(t),b[o],_,"mouseout","remove",a))}})),t.send({type:"compute_exec_schedule",cell_metadata_by_id:b(o)}),()=>{v(o),o.notebook.events.unbind("execute.CodeCell",d),o.notebook.events.unbind("select.Cell",p)}})(o);o.notebook.events.on("spec_changed.Kernel",(()=>{t()}))}))}))})(),t})()));
//# sourceMappingURL=index.js.map