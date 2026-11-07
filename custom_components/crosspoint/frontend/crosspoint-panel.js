var xt=Object.defineProperty;var wt=(r,t,e)=>t in r?xt(r,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):r[t]=e;var L=(r,t,e)=>wt(r,typeof t!="symbol"?t+"":t,e);var O=globalThis,T=O.ShadowRoot&&(O.ShadyCSS===void 0||O.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,D=Symbol(),et=new WeakMap,S=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==D)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(T&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=et.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&et.set(e,t))}return t}toString(){return this.cssText}},st=r=>new S(typeof r=="string"?r:r+"",void 0,D),B=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((s,i,n)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+r[n+1],r[0]);return new S(e,r,D)},it=(r,t)=>{if(T)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=O.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,r.appendChild(s)}},j=T?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return st(e)})(r):r;var{is:At,defineProperty:St,getOwnPropertyDescriptor:kt,getOwnPropertyNames:Et,getOwnPropertySymbols:Ct,getPrototypeOf:Pt}=Object,I=globalThis,rt=I.trustedTypes,Mt=rt?rt.emptyScript:"",Nt=I.reactiveElementPolyfillSupport,k=(r,t)=>r,q={toAttribute(r,t){switch(t){case Boolean:r=r?Mt:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},nt=(r,t)=>!At(r,t),ot={attribute:!0,type:String,converter:q,reflect:!1,useDefault:!1,hasChanged:nt};Symbol.metadata??=Symbol("metadata"),I.litPropertyMetadata??=new WeakMap;var f=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ot){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&St(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:n}=kt(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:i,set(o){let c=i?.call(this);n?.call(this,o),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ot}static _$Ei(){if(this.hasOwnProperty(k("elementProperties")))return;let t=Pt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(k("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(k("properties"))){let e=this.properties,s=[...Et(e),...Ct(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(j(i))}else t!==void 0&&e.push(j(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return it(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let n=(s.converter?.toAttribute!==void 0?s.converter:q).toAttribute(e,s.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let n=s.getPropertyOptions(i),o=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:q;this._$Em=i;let c=o.fromAttribute(e,n.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,e,s,i=!1,n){if(t!==void 0){let o=this.constructor;if(i===!1&&(n=this[t]),s??=o.getPropertyOptions(t),!((s.hasChanged??nt)(n,e)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:n},o){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),n!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,n]of s){let{wrapped:o}=n,c=this[i];o!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,n,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};f.elementStyles=[],f.shadowRootOptions={mode:"open"},f[k("elementProperties")]=new Map,f[k("finalized")]=new Map,Nt?.({ReactiveElement:f}),(I.reactiveElementVersions??=[]).push("2.1.2");var Y=globalThis,at=r=>r,H=Y.trustedTypes,lt=H?H.createPolicy("lit-html",{createHTML:r=>r}):void 0,_t="$lit$",g=`lit$${Math.random().toFixed(9).slice(2)}$`,ft="?"+g,Rt=`<${ft}>`,y=document,C=()=>y.createComment(""),P=r=>r===null||typeof r!="object"&&typeof r!="function",Z=Array.isArray,Ut=r=>Z(r)||typeof r?.[Symbol.iterator]=="function",W=`[ 	
\f\r]`,E=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ct=/-->/g,dt=/>/g,v=RegExp(`>|${W}(?:([^\\s"'>=/]+)(${W}*=${W}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ht=/'/g,pt=/"/g,mt=/^(?:script|style|textarea|title)$/i,Q=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),h=Q(1),Vt=Q(2),Ft=Q(3),x=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),ut=new WeakMap,$=y.createTreeWalker(y,129);function gt(r,t){if(!Z(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return lt!==void 0?lt.createHTML(t):t}var Ot=(r,t)=>{let e=r.length-1,s=[],i,n=t===2?"<svg>":t===3?"<math>":"",o=E;for(let c=0;c<e;c++){let a=r[c],d,u,p=-1,_=0;for(;_<a.length&&(o.lastIndex=_,u=o.exec(a),u!==null);)_=o.lastIndex,o===E?u[1]==="!--"?o=ct:u[1]!==void 0?o=dt:u[2]!==void 0?(mt.test(u[2])&&(i=RegExp("</"+u[2],"g")),o=v):u[3]!==void 0&&(o=v):o===v?u[0]===">"?(o=i??E,p=-1):u[1]===void 0?p=-2:(p=o.lastIndex-u[2].length,d=u[1],o=u[3]===void 0?v:u[3]==='"'?pt:ht):o===pt||o===ht?o=v:o===ct||o===dt?o=E:(o=v,i=void 0);let m=o===v&&r[c+1].startsWith("/>")?" ":"";n+=o===E?a+Rt:p>=0?(s.push(d),a.slice(0,p)+_t+a.slice(p)+g+m):a+g+(p===-2?c:m)}return[gt(r,n+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},M=class r{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let n=0,o=0,c=t.length-1,a=this.parts,[d,u]=Ot(t,e);if(this.el=r.createElement(d,s),$.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=$.nextNode())!==null&&a.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(let p of i.getAttributeNames())if(p.endsWith(_t)){let _=u[o++],m=i.getAttribute(p).split(g),U=/([.?@])?(.*)/.exec(_);a.push({type:1,index:n,name:U[2],strings:m,ctor:U[1]==="."?F:U[1]==="?"?K:U[1]==="@"?J:A}),i.removeAttribute(p)}else p.startsWith(g)&&(a.push({type:6,index:n}),i.removeAttribute(p));if(mt.test(i.tagName)){let p=i.textContent.split(g),_=p.length-1;if(_>0){i.textContent=H?H.emptyScript:"";for(let m=0;m<_;m++)i.append(p[m],C()),$.nextNode(),a.push({type:2,index:++n});i.append(p[_],C())}}}else if(i.nodeType===8)if(i.data===ft)a.push({type:2,index:n});else{let p=-1;for(;(p=i.data.indexOf(g,p+1))!==-1;)a.push({type:7,index:n}),p+=g.length-1}n++}}static createElement(t,e){let s=y.createElement("template");return s.innerHTML=t,s}};function w(r,t,e=r,s){if(t===x)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,n=P(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(r),i._$AT(r,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=w(r,i._$AS(r,t.values),i,s)),t}var V=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??y).importNode(e,!0);$.currentNode=i;let n=$.nextNode(),o=0,c=0,a=s[0];for(;a!==void 0;){if(o===a.index){let d;a.type===2?d=new N(n,n.nextSibling,this,t):a.type===1?d=new a.ctor(n,a.name,a.strings,this,t):a.type===6&&(d=new G(n,this,t)),this._$AV.push(d),a=s[++c]}o!==a?.index&&(n=$.nextNode(),o++)}return $.currentNode=y,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},N=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=w(this,t,e),P(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==x&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ut(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&P(this._$AH)?this._$AA.nextSibling.data=t:this.T(y.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=M.createElement(gt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let n=new V(i,this),o=n.u(this.options);n.p(e),this.T(o),this._$AH=n}}_$AC(t){let e=ut.get(t.strings);return e===void 0&&ut.set(t.strings,e=new M(t)),e}k(t){Z(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let n of t)i===e.length?e.push(s=new r(this.O(C()),this.O(C()),this,this.options)):s=e[i],s._$AI(n),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=at(t).nextSibling;at(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},A=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,n){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=l}_$AI(t,e=this,s,i){let n=this.strings,o=!1;if(n===void 0)t=w(this,t,e,0),o=!P(t)||t!==this._$AH&&t!==x,o&&(this._$AH=t);else{let c=t,a,d;for(t=n[0],a=0;a<n.length-1;a++)d=w(this,c[s+a],e,a),d===x&&(d=this._$AH[a]),o||=!P(d)||d!==this._$AH[a],d===l?t=l:t!==l&&(t+=(d??"")+n[a+1]),this._$AH[a]=d}o&&!i&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},F=class extends A{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},K=class extends A{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},J=class extends A{constructor(t,e,s,i,n){super(t,e,s,i,n),this.type=5}_$AI(t,e=this){if((t=w(this,t,e,0)??l)===x)return;let s=this._$AH,i=t===l&&s!==l||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==l&&(s===l||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},G=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){w(this,t)}};var Tt=Y.litHtmlPolyfillSupport;Tt?.(M,N),(Y.litHtmlVersions??=[]).push("3.3.3");var bt=(r,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let n=e?.renderBefore??null;s._$litPart$=i=new N(t.insertBefore(C(),n),n,void 0,e??{})}return i._$AI(r),i};var X=globalThis,b=class extends f{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=bt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return x}};b._$litElement$=!0,b.finalized=!0,X.litElementHydrateSupport?.({LitElement:b});var It=X.litElementPolyfillSupport;It?.({LitElement:b});(X.litElementVersions??=[]).push("4.2.2");var tt={en:{title:"CrossPoint",online:"Online",offline:"Offline",offline_hint:"The e-reader is not reachable. Put it in File Transfer mode to send or remove files.",no_entries:"No CrossPoint e-reader is configured.",loading:"Loading\u2026",rescan:"Rescan library",reconcile:"Sync with device",search:"Search",tab_books:"Books",tab_wallpapers:"Wallpapers",empty_books:"No books. Copy EPUB files into the books folder of the library.",empty_wallpapers:"No wallpapers. Copy images into the wallpapers folder of the library.",status_not_installed:"Not on device",status_installed:"On device",status_modified:"Modified since sent",status_missing_from_library:"Missing from library",send:"Send",resend:"Send again",remove:"Remove",cancel:"Cancel",mode_normal:"Normal",mode_transparent:"Transparent",mode:"Mode",sent_as:"Sent as {mode}",unknown_author:"Unknown author",sending:"Sending\u2026 {percent}%",confirm_remove_title:"Remove from the e-reader?",confirm_remove_text:"{name} will be deleted from the e-reader.",confirm_overwrite_title:"Replace the file on the e-reader?",confirm_overwrite_text:"{name} already exists on the e-reader and was not sent by Home Assistant. Replace it?",replace:"Replace",confirm_forget_title:"File not found on the e-reader",confirm_forget_text:"{name} is no longer on the e-reader. Stop tracking it?",forget:"Stop tracking",confirm_opaque_title:"Image without transparency",confirm_opaque_text:"{name} has no transparent pixels: as a transparent overlay it will cover the whole screen. Send it anyway?",send_anyway:"Send anyway",done_sent:"{name} sent to the e-reader.",done_removed:"{name} removed from the e-reader.",done_reconciled:"Synced with the e-reader: {removed} no longer on it, {adopted} found.",device_info:"{model} \xB7 {host}",firmware:"firmware {version}",reader_id:"reader {id}",known_readers:"{count} readers known",stats_title:"Reading stats",stats_no_users:"No reading stats users. Add one in the CrossPoint integration (Add reading stats user).",stats_unavailable:"Statistics not available",stat_reading_time:"Reading time",stat_books_finished:"Books finished",stat_pages_read:"Pages read",stat_reading_sessions:"Sessions",stat_current_streak:"Current streak",stat_longest_streak:"Longest streak",stat_last_upload:"Last upload",by_weekday:"Reading by weekday",days:"{count} d",hours_minutes:"{hours} h {minutes} min",minutes:"{minutes} min",weekdays:"Mon,Tue,Wed,Thu,Fri,Sat,Sun"},it:{title:"CrossPoint",online:"Online",offline:"Offline",offline_hint:"L'e-reader non \xE8 raggiungibile. Mettilo in modalit\xE0 File Transfer per inviare o rimuovere file.",no_entries:"Nessun e-reader CrossPoint configurato.",loading:"Caricamento\u2026",rescan:"Riscansiona libreria",reconcile:"Sincronizza con dispositivo",search:"Cerca",tab_books:"Libri",tab_wallpapers:"Sfondi",empty_books:"Nessun libro. Copia dei file EPUB nella cartella libri della libreria.",empty_wallpapers:"Nessuno sfondo. Copia delle immagini nella cartella sfondi della libreria.",status_not_installed:"Non sul dispositivo",status_installed:"Sul dispositivo",status_modified:"Modificato dopo l'invio",status_missing_from_library:"Mancante dalla libreria",send:"Invia",resend:"Invia di nuovo",remove:"Rimuovi",cancel:"Annulla",mode_normal:"Normale",mode_transparent:"Trasparente",mode:"Modalit\xE0",sent_as:"Inviato come {mode}",unknown_author:"Autore sconosciuto",sending:"Invio\u2026 {percent}%",confirm_remove_title:"Rimuovere dall'e-reader?",confirm_remove_text:"{name} verr\xE0 eliminato dall'e-reader.",confirm_overwrite_title:"Sostituire il file sull'e-reader?",confirm_overwrite_text:"{name} esiste gi\xE0 sull'e-reader e non \xE8 stato inviato da Home Assistant. Sostituirlo?",replace:"Sostituisci",confirm_forget_title:"File non trovato sull'e-reader",confirm_forget_text:"{name} non \xE8 pi\xF9 sull'e-reader. Smettere di tracciarlo?",forget:"Smetti di tracciare",confirm_opaque_title:"Immagine senza trasparenza",confirm_opaque_text:"{name} non ha pixel trasparenti: come overlay trasparente coprir\xE0 tutto lo schermo. Inviarla comunque?",send_anyway:"Invia comunque",done_sent:"{name} inviato all'e-reader.",done_removed:"{name} rimosso dall'e-reader.",done_reconciled:"Sincronizzato con l'e-reader: {removed} non pi\xF9 presenti, {adopted} trovati.",device_info:"{model} \xB7 {host}",firmware:"firmware {version}",reader_id:"lettore {id}",known_readers:"{count} lettori noti",stats_title:"Statistiche di lettura",stats_no_users:"Nessun utente statistiche. Aggiungine uno nell'integrazione CrossPoint (Aggiungi utente statistiche).",stats_unavailable:"Statistiche non disponibili",stat_reading_time:"Tempo di lettura",stat_books_finished:"Libri finiti",stat_pages_read:"Pagine lette",stat_reading_sessions:"Sessioni",stat_current_streak:"Serie attuale",stat_longest_streak:"Serie pi\xF9 lunga",stat_last_upload:"Ultimo caricamento",by_weekday:"Lettura per giorno",days:"{count} g",hours_minutes:"{hours} h {minutes} min",minutes:"{minutes} min",weekdays:"Lun,Mar,Mer,Gio,Ven,Sab,Dom"}};function vt(r){let t=(r?.locale?.language||r?.language||"en").split("-")[0],e=tt[t]||tt.en;return(s,i={})=>(e[s]??tt.en[s]??s).replace(/\{(\w+)\}/g,(o,c)=>String(i[c]??""))}var $t=B`
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    --cp-radius: var(--ha-card-border-radius, 12px);
    --cp-ok: var(--success-color, #43a047);
    --cp-warn: var(--warning-color, #ffa600);
    --cp-error: var(--error-color, #db4437);
    --cp-muted: var(--secondary-text-color);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    height: var(--header-height, 56px);
    padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    border-bottom: var(--app-header-border-bottom, none);
    box-sizing: border-box;
  }
  .toolbar .title {
    flex: 1;
    font-size: 20px;
    font-weight: 400;
    margin-left: 8px;
  }
  .toolbar select {
    font: inherit;
    color: inherit;
    background: transparent;
    border: 1px solid currentColor;
    border-radius: 6px;
    padding: 4px 6px;
  }
  .toolbar select option {
    color: var(--primary-text-color);
    background: var(--card-background-color);
  }
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 16px;
  }
  .status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
    background: var(--secondary-background-color);
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--cp-muted);
  }
  .chip.online .dot {
    background: var(--cp-ok);
  }
  .device {
    color: var(--cp-muted);
    font-size: 14px;
  }
  .spacer {
    flex: 1;
  }
  .banner {
    padding: 12px 16px;
    border-radius: var(--cp-radius);
    background: var(--secondary-background-color);
    border-left: 4px solid var(--cp-warn);
    margin-bottom: 16px;
    font-size: 14px;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
  }
  .tabs {
    display: flex;
    border-bottom: 1px solid var(--divider-color);
    flex: 1;
    min-width: 220px;
  }
  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--cp-muted);
    font: inherit;
    font-weight: 500;
    padding: 10px 16px;
    cursor: pointer;
  }
  .tab[aria-selected="true"] {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
  }
  .count {
    font-weight: 400;
    margin-left: 4px;
  }
  input[type="search"] {
    font: inherit;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    min-width: 200px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 16px;
  }
  .card {
    display: flex;
    flex-direction: column;
    background: var(--card-background-color);
    border-radius: var(--cp-radius);
    box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.14));
    border: var(--ha-card-border-width, 1px) solid
      var(--ha-card-border-color, var(--divider-color));
    overflow: hidden;
  }
  .thumb {
    aspect-ratio: 3 / 4;
    background: var(--secondary-background-color);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .thumb .placeholder {
    padding: 12px;
    text-align: center;
    color: var(--cp-muted);
    font-size: 14px;
  }
  .wallpapers .thumb {
    aspect-ratio: 3 / 5;
  }
  .body {
    padding: 10px 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }
  .name {
    font-weight: 500;
    font-size: 14px;
    line-height: 1.3;
    overflow-wrap: anywhere;
  }
  .meta {
    color: var(--cp-muted);
    font-size: 13px;
  }
  .badge {
    align-self: flex-start;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--cp-muted);
  }
  .badge.installed {
    color: var(--cp-ok);
  }
  .badge.modified {
    color: var(--cp-warn);
  }
  .badge.missing_from_library {
    color: var(--cp-error);
  }
  .progress {
    height: 4px;
    border-radius: 2px;
    background: var(--divider-color);
    overflow: hidden;
  }
  .progress div {
    height: 100%;
    background: var(--primary-color);
    transition: width 0.2s;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: auto;
    padding-top: 4px;
  }
  button.action {
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 16px;
    border: 1px solid var(--primary-color);
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    cursor: pointer;
  }
  button.action.secondary {
    background: transparent;
    color: var(--primary-color);
  }
  button.action.danger {
    background: transparent;
    border-color: var(--cp-error);
    color: var(--cp-error);
  }
  button.action:disabled {
    opacity: 0.4;
    cursor: default;
  }
  button.action.toolbar-button {
    background: transparent;
    border-color: currentColor;
    color: inherit;
  }
  .segmented {
    display: inline-flex;
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    overflow: hidden;
  }
  .segmented button {
    font: inherit;
    font-size: 12px;
    padding: 4px 10px;
    border: none;
    background: transparent;
    color: var(--cp-muted);
    cursor: pointer;
  }
  .segmented button[aria-pressed="true"] {
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .empty {
    padding: 48px 16px;
    text-align: center;
    color: var(--cp-muted);
  }
  .scrim {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    padding: 16px;
  }
  .dialog {
    background: var(--card-background-color);
    color: var(--primary-text-color);
    border-radius: var(--cp-radius);
    padding: 20px 24px 16px;
    max-width: 420px;
    width: 100%;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }
  .dialog h2 {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 500;
  }
  .dialog p {
    margin: 0 0 16px;
    color: var(--cp-muted);
    line-height: 1.4;
  }
  .dialog .actions {
    justify-content: flex-end;
  }
  @media (max-width: 600px) {
    main {
      padding: 12px;
    }
    .grid {
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }
    input[type="search"] {
      flex: 1;
      min-width: 0;
    }
  }
`;var yt="crosspoint-panel",Ht=1500;function zt(){try{return JSON.parse(window.localStorage.getItem(yt))||{}}catch{return{}}}function Lt(r){try{window.localStorage.setItem(yt,JSON.stringify(r))}catch{}}function z(r){return r.split("/").pop()}var R=class extends b{constructor(){super();let t=zt();this._entries=void 0,this._entryId=t.entryId,this._state=void 0,this._tab=t.tab==="wallpapers"?"wallpapers":"books",this._filter="",this._busy=new Set,this._progress={},this._modes={},this._dialog=void 0,this._unsubscribe=void 0,this._connected=!1}connectedCallback(){super.connectedCallback(),this._connected=!0,this.hass&&this._load()}disconnectedCallback(){super.disconnectedCallback(),this._connected=!1,this._unsubscribeState()}willUpdate(t){t.has("hass")&&(this._t=vt(this.hass),!t.get("hass")&&this._connected&&this._load())}async _load(){try{this._entries=await this.hass.callWS({type:"crosspoint/entries"})}catch(t){this._error=t.message;return}this._entries.some(t=>t.entry_id===this._entryId)||(this._entryId=this._entries[0]?.entry_id),this._subscribe()}async _subscribe(){if(this._unsubscribeState(),this._state=void 0,!this._entryId)return;let t=this._entryId;try{this._unsubscribe=await this.hass.connection.subscribeMessage(e=>this._onEvent(t,e),{type:"crosspoint/subscribe",entry_id:t})}catch(e){this._error=e.message}}_unsubscribeState(){this._unsubscribe&&(this._unsubscribe().catch(()=>{}),this._unsubscribe=void 0)}_onEvent(t,e){t===this._entryId&&(e.type==="state"?(this._state=e,this._error=void 0):e.type==="progress"?this._progress={...this._progress,[`${e.kind}:${e.file}`]:e.received/Math.max(e.total,1)}:e.type==="closed"&&(this._unsubscribe=void 0,setTimeout(()=>this._connected&&this._load(),Ht)))}_selectEntry(t){this._entryId=t,this._savePrefs(),this._subscribe()}_selectTab(t){this._tab=t,this._savePrefs()}_savePrefs(){Lt({entryId:this._entryId,tab:this._tab})}_call(t,e){return this.hass.callWS({type:t,entry_id:this._entryId,...e})}async _run(t,e){this._busy=new Set(this._busy).add(t);try{return await e()}finally{let s=new Set(this._busy);s.delete(t),this._busy=s;let{[t]:i,...n}=this._progress;this._progress=n}}_toast(t){this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:t},bubbles:!0,composed:!0}))}_confirm({title:t,text:e,confirm:s,danger:i=!1}){return new Promise(n=>{this._dialog={title:t,text:e,confirm:s,danger:i,resolve:n}})}_closeDialog(t){this._dialog?.resolve(t),this._dialog=void 0}async _send(t,e){let s=`${t}:${e.file}`,i=e.title||z(e.file),n=this._modeOf(e);await this._run(s,async()=>{let o={};if(t==="wallpaper"&&n==="transparent"&&!(await this._call("crosspoint/wallpaper_check",{file:e.file})).has_transparency){if(!await this._confirm({title:this._t("confirm_opaque_title"),text:this._t("confirm_opaque_text",{name:i}),confirm:this._t("send_anyway")}))return;o.force=!0}let c=t==="book"?"crosspoint/send_book":"crosspoint/send_wallpaper",a=t==="book"?{}:{mode:n};for(;;)try{await this._call(c,{file:e.file,...a,...o}),this._toast(this._t("done_sent",{name:i}));return}catch(d){if(d.translation_key==="file_exists_on_device"&&!o.overwrite){if(!await this._confirm({title:this._t("confirm_overwrite_title"),text:this._t("confirm_overwrite_text",{name:i}),confirm:this._t("replace"),danger:!0}))return;o.overwrite=!0;continue}this._toast(d.message);return}})}async _remove(t,e){let s=`${t}:${e.file}`,i=e.title||z(e.file);if(!await this._confirm({title:this._t("confirm_remove_title"),text:this._t("confirm_remove_text",{name:i}),confirm:this._t("remove"),danger:!0}))return;let o=t==="book"?"crosspoint/remove_book":"crosspoint/remove_wallpaper";await this._run(s,async()=>{try{await this._call(o,{file:e.file})}catch(c){if(c.translation_key!=="not_on_device"){this._toast(c.message);return}if(!await this._confirm({title:this._t("confirm_forget_title"),text:this._t("confirm_forget_text",{name:i}),confirm:this._t("forget")}))return;try{await this._call(o,{file:e.file,forget_missing:!0})}catch(d){this._toast(d.message);return}}this._toast(this._t("done_removed",{name:i}))})}async _rescan(){await this._run("rescan",async()=>{try{await this._call("crosspoint/rescan",{})}catch(t){this._toast(t.message)}})}async _reconcile(){await this._run("reconcile",async()=>{try{let{removed:t,adopted:e}=await this._call("crosspoint/reconcile",{});this._toast(this._t("done_reconciled",{removed:t,adopted:e}))}catch(t){this._toast(t.message)}})}_modeOf(t){return this._modes[t.file]||t.mode||"normal"}_setMode(t,e){this._modes={...this._modes,[t.file]:e}}render(){if(!this.hass||!this._t)return l;let t=this._t;return h`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${t("title")}</div>
        ${this._entries?.length>1?h`<select
              aria-label="E-reader"
              @change=${e=>this._selectEntry(e.target.value)}
            >
              ${this._entries.map(e=>h`<option value=${e.entry_id} ?selected=${e.entry_id===this._entryId}>
                    ${e.title}
                  </option>`)}
            </select>`:l}
        ${this._state?h`<button
              class="action toolbar-button"
              ?disabled=${!this._state.online||this._busy.has("reconcile")}
              @click=${this._reconcile}
            >
              ${t("reconcile")}
            </button>`:l}
        ${this._state?h`<button
              class="action toolbar-button"
              ?disabled=${this._busy.has("rescan")}
              @click=${this._rescan}
            >
              ${t("rescan")}
            </button>`:l}
      </div>
      <main>${this._renderMain()}</main>
      ${this._renderDialog()}
    `}_renderMain(){let t=this._t;if(this._error&&!this._state)return h`<div class="empty">${this._error}</div>`;if(this._entries&&this._entries.length===0)return h`<div class="empty">${t("no_entries")}</div>`;let e=this._state;if(!e)return h`<div class="empty">${t("loading")}</div>`;let s=this._tab==="books"?e.books:e.wallpapers,i=this._filter.trim().toLowerCase(),n=i?s.filter(o=>[o.file,o.title,...o.authors||[]].filter(Boolean).some(c=>c.toLowerCase().includes(i))):s;return h`
      <div class="status">
        <span class="chip ${e.online?"online":""}">
          <span class="dot"></span>${e.online?t("online"):t("offline")}
        </span>
        <span class="device">
          ${t("device_info",{model:e.model.name,host:e.host})}
          ${e.firmware?h` · ${t("firmware",{version:e.firmware})}`:l}
          ${e.active_device?h` · ${t("reader_id",{id:e.active_device.slice(0,8)})}`:l}
          ${e.devices?.length>1?h` · ${t("known_readers",{count:e.devices.length})}`:l}
        </span>
      </div>
      ${e.online?l:h`<div class="banner">${t("offline_hint")}</div>`}
      <div class="controls">
        <div class="tabs" role="tablist">
          ${["books","wallpapers"].map(o=>h`<button
              class="tab"
              role="tab"
              aria-selected=${this._tab===o}
              @click=${()=>this._selectTab(o)}
            >
              ${t(`tab_${o}`)}<span class="count">(${e[o].length})</span>
            </button>`)}
        </div>
        <input
          type="search"
          placeholder=${t("search")}
          aria-label=${t("search")}
          .value=${this._filter}
          @input=${o=>{this._filter=o.target.value}}
        />
      </div>
      ${n.length===0?h`<div class="empty">
            ${s.length===0?t(`empty_${this._tab}`):l}
          </div>`:h`<div class="grid ${this._tab}">
            ${n.map(o=>this._tab==="books"?this._renderItem("book",o,e.online):this._renderItem("wallpaper",o,e.online))}
          </div>`}
    `}_renderItem(t,e,s){let i=this._t,n=`${t}:${e.file}`,o=this._busy.has(n),c=this._progress[n],a=e.status!=="missing_from_library",d=e.status!=="not_installed",u=t==="book"&&e.title||z(e.file),p=this._modeOf(e);return h`
      <div class="card">
        <div class="thumb">
          ${e.thumbnail_url?h`<img src=${e.thumbnail_url} alt="" loading="lazy" />`:h`<div class="placeholder">${u}</div>`}
        </div>
        <div class="body">
          <div class="name">${u}</div>
          ${t==="book"?h`<div class="meta">
                ${e.authors?.length?e.authors.join(", "):i("unknown_author")}
              </div>`:e.mode&&d?h`<div class="meta">
                  ${i("sent_as",{mode:i(`mode_${e.mode}`).toLowerCase()})}
                </div>`:l}
          <span class="badge ${e.status}">${i(`status_${e.status}`)}</span>
          ${o&&c!==void 0?h`<div class="meta">
                  ${i("sending",{percent:Math.round(c*100)})}
                </div>
                <div class="progress"><div style="width:${c*100}%"></div></div>`:l}
          ${t==="wallpaper"&&a?h`<div class="segmented" role="group" aria-label=${i("mode")}>
                ${["normal","transparent"].map(_=>h`<button
                    aria-pressed=${p===_}
                    ?disabled=${o}
                    @click=${()=>this._setMode(e,_)}
                  >
                    ${i(`mode_${_}`)}
                  </button>`)}
              </div>`:l}
          <div class="actions">
            ${a?h`<button
                  class="action ${e.status==="installed"?"secondary":""}"
                  ?disabled=${!s||o}
                  @click=${()=>this._send(t,e)}
                >
                  ${i(d?"resend":"send")}
                </button>`:l}
            ${d?h`<button
                  class="action danger"
                  ?disabled=${!s||o}
                  @click=${()=>this._remove(t,e)}
                >
                  ${i("remove")}
                </button>`:l}
          </div>
        </div>
      </div>
    `}_renderDialog(){let t=this._dialog;return t?h`
      <div class="scrim" @click=${e=>e.target===e.currentTarget&&this._closeDialog(!1)}>
        <div class="dialog" role="alertdialog" aria-modal="true" aria-label=${t.title}>
          <h2>${t.title}</h2>
          <p>${t.text}</p>
          <div class="actions">
            <button class="action secondary" @click=${()=>this._closeDialog(!1)}>
              ${this._t("cancel")}
            </button>
            <button
              class="action ${t.danger?"danger":""}"
              @click=${()=>this._closeDialog(!0)}
            >
              ${t.confirm}
            </button>
          </div>
        </div>
      </div>
    `:l}};L(R,"properties",{hass:{attribute:!1},narrow:{type:Boolean},panel:{attribute:!1},_entries:{state:!0},_entryId:{state:!0},_state:{state:!0},_tab:{state:!0},_filter:{state:!0},_busy:{state:!0},_progress:{state:!0},_modes:{state:!0},_dialog:{state:!0},_error:{state:!0}}),L(R,"styles",$t);customElements.get("crosspoint-panel")||customElements.define("crosspoint-panel",R);
