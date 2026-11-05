var be=Object.defineProperty;var Ae=(n,e,t)=>e in n?be(n,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):n[e]=t;var z=(n,e,t)=>Ae(n,typeof e!="symbol"?e+"":e,t);var T=globalThis,O=T.ShadowRoot&&(T.ShadyCSS===void 0||T.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,I=Symbol(),ee=new WeakMap,x=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==I)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(O&&e===void 0){let s=t!==void 0&&t.length===1;s&&(e=ee.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&ee.set(t,e))}return e}toString(){return this.cssText}},te=n=>new x(typeof n=="string"?n:n+"",void 0,I),D=(n,...e)=>{let t=n.length===1?n[0]:e.reduce((s,i,r)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+n[r+1],n[0]);return new x(t,n,I)},se=(n,e)=>{if(O)n.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let s=document.createElement("style"),i=T.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=t.cssText,n.appendChild(s)}},B=O?n=>n:n=>n instanceof CSSStyleSheet?(e=>{let t="";for(let s of e.cssRules)t+=s.cssText;return te(t)})(n):n;var{is:Se,defineProperty:we,getOwnPropertyDescriptor:xe,getOwnPropertyNames:Ee,getOwnPropertySymbols:Ce,getPrototypeOf:Pe}=Object,H=globalThis,ie=H.trustedTypes,ke=ie?ie.emptyScript:"",Ne=H.reactiveElementPolyfillSupport,E=(n,e)=>n,j={toAttribute(n,e){switch(e){case Boolean:n=n?ke:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,e){let t=n;switch(e){case Boolean:t=n!==null;break;case Number:t=n===null?null:Number(n);break;case Object:case Array:try{t=JSON.parse(n)}catch{t=null}}return t}},re=(n,e)=>!Se(n,e),ne={attribute:!0,type:String,converter:j,reflect:!1,useDefault:!1,hasChanged:re};Symbol.metadata??=Symbol("metadata"),H.litPropertyMetadata??=new WeakMap;var _=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=ne){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(e,s,t);i!==void 0&&we(this.prototype,e,i)}}static getPropertyDescriptor(e,t,s){let{get:i,set:r}=xe(this.prototype,e)??{get(){return this[t]},set(o){this[t]=o}};return{get:i,set(o){let a=i?.call(this);r?.call(this,o),this.requestUpdate(e,a,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ne}static _$Ei(){if(this.hasOwnProperty(E("elementProperties")))return;let e=Pe(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(E("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(E("properties"))){let t=this.properties,s=[...Ee(t),...Ce(t)];for(let i of s)this.createProperty(i,t[i])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[s,i]of t)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[t,s]of this.elementProperties){let i=this._$Eu(t,s);i!==void 0&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let s=new Set(e.flat(1/0).reverse());for(let i of s)t.unshift(B(i))}else e!==void 0&&t.push(B(e));return t}static _$Eu(e,t){let s=t.attribute;return s===!1?void 0:typeof s=="string"?s:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return se(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){let s=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,s);if(i!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:j).toAttribute(t,s.type);this._$Em=e,r==null?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(e,t){let s=this.constructor,i=s._$Eh.get(e);if(i!==void 0&&this._$Em!==i){let r=s.getPropertyOptions(i),o=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:j;this._$Em=i;let a=o.fromAttribute(t,r.type);this[i]=a??this._$Ej?.get(i)??a,this._$Em=null}}requestUpdate(e,t,s,i=!1,r){if(e!==void 0){let o=this.constructor;if(i===!1&&(r=this[e]),s??=o.getPropertyOptions(e),!((s.hasChanged??re)(r,t)||s.useDefault&&s.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,s))))return;this.C(e,t,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:i,wrapped:r},o){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),r!==!0||o!==void 0)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),i===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,r]of this._$Ep)this[i]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,r]of s){let{wrapped:o}=r,a=this[i];o!==!0||this._$AL.has(i)||a===void 0||this.C(i,void 0,r,a)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};_.elementStyles=[],_.shadowRootOptions={mode:"open"},_[E("elementProperties")]=new Map,_[E("finalized")]=new Map,Ne?.({ReactiveElement:_}),(H.reactiveElementVersions??=[]).push("2.1.2");var J=globalThis,oe=n=>n,L=J.trustedTypes,ae=L?L.createPolicy("lit-html",{createHTML:n=>n}):void 0,ue="$lit$",g=`lit$${Math.random().toFixed(9).slice(2)}$`,me="?"+g,Me=`<${me}>`,b=document,P=()=>b.createComment(""),k=n=>n===null||typeof n!="object"&&typeof n!="function",X=Array.isArray,Ue=n=>X(n)||typeof n?.[Symbol.iterator]=="function",W=`[ 	
\f\r]`,C=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,le=/-->/g,de=/>/g,v=RegExp(`>|${W}(?:([^\\s"'>=/]+)(${W}*=${W}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ce=/'/g,he=/"/g,_e=/^(?:script|style|textarea|title)$/i,Z=n=>(e,...t)=>({_$litType$:n,strings:e,values:t}),u=Z(1),je=Z(2),We=Z(3),A=Symbol.for("lit-noChange"),c=Symbol.for("lit-nothing"),pe=new WeakMap,y=b.createTreeWalker(b,129);function fe(n,e){if(!X(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return ae!==void 0?ae.createHTML(e):e}var Re=(n,e)=>{let t=n.length-1,s=[],i,r=e===2?"<svg>":e===3?"<math>":"",o=C;for(let a=0;a<t;a++){let l=n[a],h,p,d=-1,m=0;for(;m<l.length&&(o.lastIndex=m,p=o.exec(l),p!==null);)m=o.lastIndex,o===C?p[1]==="!--"?o=le:p[1]!==void 0?o=de:p[2]!==void 0?(_e.test(p[2])&&(i=RegExp("</"+p[2],"g")),o=v):p[3]!==void 0&&(o=v):o===v?p[0]===">"?(o=i??C,d=-1):p[1]===void 0?d=-2:(d=o.lastIndex-p[2].length,h=p[1],o=p[3]===void 0?v:p[3]==='"'?he:ce):o===he||o===ce?o=v:o===le||o===de?o=C:(o=v,i=void 0);let f=o===v&&n[a+1].startsWith("/>")?" ":"";r+=o===C?l+Me:d>=0?(s.push(h),l.slice(0,d)+ue+l.slice(d)+g+f):l+g+(d===-2?a:f)}return[fe(n,r+(n[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),s]},N=class n{constructor({strings:e,_$litType$:t},s){let i;this.parts=[];let r=0,o=0,a=e.length-1,l=this.parts,[h,p]=Re(e,t);if(this.el=n.createElement(h,s),y.currentNode=this.el.content,t===2||t===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(i=y.nextNode())!==null&&l.length<a;){if(i.nodeType===1){if(i.hasAttributes())for(let d of i.getAttributeNames())if(d.endsWith(ue)){let m=p[o++],f=i.getAttribute(d).split(g),R=/([.?@])?(.*)/.exec(m);l.push({type:1,index:r,name:R[2],strings:f,ctor:R[1]==="."?V:R[1]==="?"?F:R[1]==="@"?K:w}),i.removeAttribute(d)}else d.startsWith(g)&&(l.push({type:6,index:r}),i.removeAttribute(d));if(_e.test(i.tagName)){let d=i.textContent.split(g),m=d.length-1;if(m>0){i.textContent=L?L.emptyScript:"";for(let f=0;f<m;f++)i.append(d[f],P()),y.nextNode(),l.push({type:2,index:++r});i.append(d[m],P())}}}else if(i.nodeType===8)if(i.data===me)l.push({type:2,index:r});else{let d=-1;for(;(d=i.data.indexOf(g,d+1))!==-1;)l.push({type:7,index:r}),d+=g.length-1}r++}}static createElement(e,t){let s=b.createElement("template");return s.innerHTML=e,s}};function S(n,e,t=n,s){if(e===A)return e;let i=s!==void 0?t._$Co?.[s]:t._$Cl,r=k(e)?void 0:e._$litDirective$;return i?.constructor!==r&&(i?._$AO?.(!1),r===void 0?i=void 0:(i=new r(n),i._$AT(n,t,s)),s!==void 0?(t._$Co??=[])[s]=i:t._$Cl=i),i!==void 0&&(e=S(n,i._$AS(n,e.values),i,s)),e}var q=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:s}=this._$AD,i=(e?.creationScope??b).importNode(t,!0);y.currentNode=i;let r=y.nextNode(),o=0,a=0,l=s[0];for(;l!==void 0;){if(o===l.index){let h;l.type===2?h=new M(r,r.nextSibling,this,e):l.type===1?h=new l.ctor(r,l.name,l.strings,this,e):l.type===6&&(h=new G(r,this,e)),this._$AV.push(h),l=s[++a]}o!==l?.index&&(r=y.nextNode(),o++)}return y.currentNode=b,i}p(e){let t=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}},M=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,i){this.type=2,this._$AH=c,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=S(this,e,t),k(e)?e===c||e==null||e===""?(this._$AH!==c&&this._$AR(),this._$AH=c):e!==this._$AH&&e!==A&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Ue(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==c&&k(this._$AH)?this._$AA.nextSibling.data=e:this.T(b.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:s}=e,i=typeof s=="number"?this._$AC(e):(s.el===void 0&&(s.el=N.createElement(fe(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(t);else{let r=new q(i,this),o=r.u(this.options);r.p(t),this.T(o),this._$AH=r}}_$AC(e){let t=pe.get(e.strings);return t===void 0&&pe.set(e.strings,t=new N(e)),t}k(e){X(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,s,i=0;for(let r of e)i===t.length?t.push(s=new n(this.O(P()),this.O(P()),this,this.options)):s=t[i],s._$AI(r),i++;i<t.length&&(this._$AR(s&&s._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let s=oe(e).nextSibling;oe(e).remove(),e=s}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},w=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,i,r){this.type=1,this._$AH=c,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=c}_$AI(e,t=this,s,i){let r=this.strings,o=!1;if(r===void 0)e=S(this,e,t,0),o=!k(e)||e!==this._$AH&&e!==A,o&&(this._$AH=e);else{let a=e,l,h;for(e=r[0],l=0;l<r.length-1;l++)h=S(this,a[s+l],t,l),h===A&&(h=this._$AH[l]),o||=!k(h)||h!==this._$AH[l],h===c?e=c:e!==c&&(e+=(h??"")+r[l+1]),this._$AH[l]=h}o&&!i&&this.j(e)}j(e){e===c?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},V=class extends w{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===c?void 0:e}},F=class extends w{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==c)}},K=class extends w{constructor(e,t,s,i,r){super(e,t,s,i,r),this.type=5}_$AI(e,t=this){if((e=S(this,e,t,0)??c)===A)return;let s=this._$AH,i=e===c&&s!==c||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,r=e!==c&&(s===c||i);i&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},G=class{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){S(this,e)}};var Te=J.litHtmlPolyfillSupport;Te?.(N,M),(J.litHtmlVersions??=[]).push("3.3.3");var ge=(n,e,t)=>{let s=t?.renderBefore??e,i=s._$litPart$;if(i===void 0){let r=t?.renderBefore??null;s._$litPart$=i=new M(e.insertBefore(P(),r),r,void 0,t??{})}return i._$AI(n),i};var Q=globalThis,$=class extends _{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=ge(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return A}};$._$litElement$=!0,$.finalized=!0,Q.litElementHydrateSupport?.({LitElement:$});var Oe=Q.litElementPolyfillSupport;Oe?.({LitElement:$});(Q.litElementVersions??=[]).push("4.2.2");var Y={en:{title:"CrossPoint",online:"Online",offline:"Offline",offline_hint:"The e-reader is not reachable. Put it in File Transfer mode to send or remove files.",no_entries:"No CrossPoint e-reader is configured.",loading:"Loading\u2026",rescan:"Rescan library",reconcile:"Sync with device",search:"Search",tab_books:"Books",tab_wallpapers:"Wallpapers",empty_books:"No books. Copy EPUB files into the books folder of the library.",empty_wallpapers:"No wallpapers. Copy images into the wallpapers folder of the library.",status_not_installed:"Not on device",status_installed:"On device",status_modified:"Modified since sent",status_missing_from_library:"Missing from library",send:"Send",resend:"Send again",remove:"Remove",cancel:"Cancel",mode_normal:"Normal",mode_transparent:"Transparent",mode:"Mode",sent_as:"Sent as {mode}",unknown_author:"Unknown author",sending:"Sending\u2026 {percent}%",confirm_remove_title:"Remove from the e-reader?",confirm_remove_text:"{name} will be deleted from the e-reader.",confirm_overwrite_title:"Replace the file on the e-reader?",confirm_overwrite_text:"{name} already exists on the e-reader and was not sent by Home Assistant. Replace it?",replace:"Replace",confirm_forget_title:"File not found on the e-reader",confirm_forget_text:"{name} is no longer on the e-reader. Stop tracking it?",forget:"Stop tracking",confirm_opaque_title:"Image without transparency",confirm_opaque_text:"{name} has no transparent pixels: as a transparent overlay it will cover the whole screen. Send it anyway?",send_anyway:"Send anyway",done_sent:"{name} sent to the e-reader.",done_removed:"{name} removed from the e-reader.",done_reconciled:"Synced with the e-reader: {removed} no longer on it, {adopted} found.",device_info:"{model} \xB7 {host}",firmware:"firmware {version}",stats_title:"Reading stats",stats_no_users:"No reading stats users. Add one in the CrossPoint integration (Add reading stats user).",stats_unavailable:"Statistics not available",stat_reading_time:"Reading time",stat_books_finished:"Books finished",stat_pages_read:"Pages read",stat_reading_sessions:"Sessions",stat_current_streak:"Current streak",stat_longest_streak:"Longest streak",stat_last_upload:"Last upload",by_weekday:"Reading by weekday",days:"{count} d",hours_minutes:"{hours} h {minutes} min",minutes:"{minutes} min",weekdays:"Mon,Tue,Wed,Thu,Fri,Sat,Sun"},it:{title:"CrossPoint",online:"Online",offline:"Offline",offline_hint:"L'e-reader non \xE8 raggiungibile. Mettilo in modalit\xE0 File Transfer per inviare o rimuovere file.",no_entries:"Nessun e-reader CrossPoint configurato.",loading:"Caricamento\u2026",rescan:"Riscansiona libreria",reconcile:"Sincronizza con dispositivo",search:"Cerca",tab_books:"Libri",tab_wallpapers:"Sfondi",empty_books:"Nessun libro. Copia dei file EPUB nella cartella libri della libreria.",empty_wallpapers:"Nessuno sfondo. Copia delle immagini nella cartella sfondi della libreria.",status_not_installed:"Non sul dispositivo",status_installed:"Sul dispositivo",status_modified:"Modificato dopo l'invio",status_missing_from_library:"Mancante dalla libreria",send:"Invia",resend:"Invia di nuovo",remove:"Rimuovi",cancel:"Annulla",mode_normal:"Normale",mode_transparent:"Trasparente",mode:"Modalit\xE0",sent_as:"Inviato come {mode}",unknown_author:"Autore sconosciuto",sending:"Invio\u2026 {percent}%",confirm_remove_title:"Rimuovere dall'e-reader?",confirm_remove_text:"{name} verr\xE0 eliminato dall'e-reader.",confirm_overwrite_title:"Sostituire il file sull'e-reader?",confirm_overwrite_text:"{name} esiste gi\xE0 sull'e-reader e non \xE8 stato inviato da Home Assistant. Sostituirlo?",replace:"Sostituisci",confirm_forget_title:"File non trovato sull'e-reader",confirm_forget_text:"{name} non \xE8 pi\xF9 sull'e-reader. Smettere di tracciarlo?",forget:"Smetti di tracciare",confirm_opaque_title:"Immagine senza trasparenza",confirm_opaque_text:"{name} non ha pixel trasparenti: come overlay trasparente coprir\xE0 tutto lo schermo. Inviarla comunque?",send_anyway:"Invia comunque",done_sent:"{name} inviato all'e-reader.",done_removed:"{name} rimosso dall'e-reader.",done_reconciled:"Sincronizzato con l'e-reader: {removed} non pi\xF9 presenti, {adopted} trovati.",device_info:"{model} \xB7 {host}",firmware:"firmware {version}",stats_title:"Statistiche di lettura",stats_no_users:"Nessun utente statistiche. Aggiungine uno nell'integrazione CrossPoint (Aggiungi utente statistiche).",stats_unavailable:"Statistiche non disponibili",stat_reading_time:"Tempo di lettura",stat_books_finished:"Libri finiti",stat_pages_read:"Pagine lette",stat_reading_sessions:"Sessioni",stat_current_streak:"Serie attuale",stat_longest_streak:"Serie pi\xF9 lunga",stat_last_upload:"Ultimo caricamento",by_weekday:"Lettura per giorno",days:"{count} g",hours_minutes:"{hours} h {minutes} min",minutes:"{minutes} min",weekdays:"Lun,Mar,Mer,Gio,Ven,Sab,Dom"}};function $e(n){let e=(n?.locale?.language||n?.language||"en").split("-")[0],t=Y[e]||Y.en;return(s,i={})=>(t[s]??Y.en[s]??s).replace(/\{(\w+)\}/g,(o,a)=>String(i[a]??""))}var ve="CrossPoint Sync ",ye=["books_finished","pages_read","reading_sessions","current_streak","longest_streak"];function He(n){let e=new Map;for(let s of Object.values(n.entities||{}))s.platform!=="crosspoint"||!s.device_id||!s.translation_key||(e.has(s.device_id)||e.set(s.device_id,{}),e.get(s.device_id)[s.translation_key]=s.entity_id);let t=[];for(let[s,i]of e){if(!i.reading_time)continue;let r=n.devices?.[s],o=r?.name_by_user||r?.name||"",a=o.startsWith(ve)?o.slice(ve.length):o;t.push({deviceId:s,name:a,entities:i})}return t.sort((s,i)=>s.name.localeCompare(i.name))}var U=class extends ${static getStubConfig(){return{}}setConfig(e){if(e.users!==void 0&&!Array.isArray(e.users))throw new Error("users must be a list of user names");this._config=e}getCardSize(){return 5}getGridOptions(){return{columns:12,min_columns:6,rows:"auto"}}_users(){let e=He(this.hass),t=this._config.users;return t?.length?t.map(s=>e.find(i=>i.name===s)).filter(Boolean):e}_state(e){return e?this.hass.states[e]:void 0}_number(e){let t=Number(this._state(e)?.state);return Number.isFinite(t)?t:void 0}_moreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_formatDuration(e){let t=this._t;if(!e)return"\u2014";let s={s:1/60,min:1,h:60,d:1440}[e.attributes.unit_of_measurement],i=Number(e.state);if(!Number.isFinite(i)||s===void 0)return"\u2014";let r=Math.round(i*s),o=Math.floor(r/60),a=r%60;return o?t("hours_minutes",{hours:o,minutes:a}):t("minutes",{minutes:a})}_formatStat(e,t){let s=this._number(t);if(s===void 0)return"\u2014";let i=s.toLocaleString(this.hass.locale?.language);return e.endsWith("streak")?this._t("days",{count:i}):i}render(){if(!this.hass||!this._config)return c;this._t=$e(this.hass);let e=this._t,t=this._users(),s=this._config.title??e("stats_title"),i=t.length>1,r={};if(i)for(let o of["reading_time",...ye])r[o]=Math.max(...t.map(a=>this._number(a.entities[o])??-1/0));return u`
      <ha-card .header=${s||void 0}>
        <div class="content ${s?"":"no-header"}">
          ${t.length===0?u`<div class="empty">${e("stats_no_users")}</div>`:u`<div class="users ${i?"compare":""}">
                ${t.map(o=>this._renderUser(o,i?r:{}))}
              </div>`}
        </div>
      </ha-card>
    `}_renderUser(e,t){let s=this._t,i=this._state(e.entities.reading_time),r=!i||i.state==="unavailable",o=a=>t[a]!==void 0&&t[a]>0&&this._number(e.entities[a])===t[a];return u`
      <div class="user">
        <div class="name">${e.name}</div>
        ${r?u`<div class="empty">${s("stats_unavailable")}</div>`:u`
              <button
                class="hero ${o("reading_time")?"best":""}"
                @click=${()=>this._moreInfo(e.entities.reading_time)}
              >
                <span class="value">${this._formatDuration(i)}</span>
                <span class="label">${s("stat_reading_time")}</span>
              </button>
              <div class="stats">
                ${ye.map(a=>u`<button
                    class="stat ${o(a)?"best":""}"
                    @click=${()=>this._moreInfo(e.entities[a])}
                  >
                    <span class="value">${this._formatStat(a,e.entities[a])}</span>
                    <span class="label">${s(`stat_${a}`)}</span>
                  </button>`)}
              </div>
              ${this._renderWeekdays(i)}
            `}
      </div>
    `}_renderWeekdays(e){let t=this._t,s=e.attributes.weekday_minutes;if(!s)return c;let i=["mon","tue","wed","thu","fri","sat","sun"],r=t("weekdays").split(","),o=Math.max(1,...i.map(a=>s[a]||0));return u`
      <div class="weekdays" role="img" aria-label=${t("by_weekday")}>
        <div class="label">${t("by_weekday")}</div>
        <div class="bars">
          ${i.map((a,l)=>u`<div class="bar" title="${r[l]}: ${t("minutes",{minutes:s[a]||0})}">
              <div class="fill" style="height:${(s[a]||0)/o*100}%"></div>
              <span>${r[l]}</span>
            </div>`)}
        </div>
      </div>
    `}};z(U,"properties",{hass:{attribute:!1},_config:{state:!0}}),z(U,"styles",D`
    .content {
      padding: 0 16px 16px;
    }
    .content.no-header {
      padding-top: 16px;
    }
    .users {
      display: grid;
      gap: 16px;
    }
    .users.compare {
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }
    .user {
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-width: 0;
    }
    .users.compare .user {
      padding: 12px;
      border-radius: 12px;
      background: var(--secondary-background-color);
    }
    .name {
      font-weight: 500;
      font-size: 16px;
    }
    button {
      font: inherit;
      color: inherit;
      text-align: left;
      background: none;
      border: none;
      padding: 0;
      cursor: pointer;
    }
    .hero .value {
      display: block;
      font-size: 28px;
      font-weight: 400;
      line-height: 1.2;
    }
    .label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 10px 12px;
    }
    .stat .value {
      display: block;
      font-size: 18px;
    }
    .best .value {
      color: var(--primary-color);
      font-weight: 500;
    }
    .weekdays .bars {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      height: 64px;
      margin-top: 6px;
    }
    .bar {
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      gap: 2px;
      min-width: 0;
    }
    .fill {
      width: 100%;
      min-height: 2px;
      border-radius: 3px 3px 0 0;
      background: var(--primary-color);
      opacity: 0.85;
    }
    .bar span {
      font-size: 10px;
      color: var(--secondary-text-color);
    }
    .empty {
      color: var(--secondary-text-color);
      padding: 8px 0;
    }
  `);customElements.get("crosspoint-stats-card")||customElements.define("crosspoint-stats-card",U);window.customCards=window.customCards||[];window.customCards.some(n=>n.type==="crosspoint-stats-card")||window.customCards.push({type:"crosspoint-stats-card",name:"CrossPoint reading stats",description:"Reading statistics from CrossPoint Sync, for one or more users.",preview:!0});
