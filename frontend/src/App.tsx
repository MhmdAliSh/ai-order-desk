import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { FileUp, ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, Boxes, Building2, Cable, Check, ChevronLeft, ChevronRight, CircleHelp, ClipboardList, Headphones, History, LayoutDashboard, LockKeyhole, LogOut, Menu, MessageCircle, Package, Plus, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Smartphone, Sparkles, TrendingUp, TriangleAlert, Wallet, X, Zap } from 'lucide-react';
import { getProducts, getSetupStatus, login, money, priceCents, readSession, setupOwner, storeSession, stockState, type AuthSession, type Product } from './api';
import { OrderWorkspace } from './OrderWorkspace';
import { OrdersPage } from './OrdersPage';
import { AiIntake } from './AiIntake';
import { AdminPage } from './AdminPage';
import { OperationsPage } from './OperationsPage';
import { SettingsPage } from './SettingsPage';
import { MessageInboxPage } from './MessageInboxPage';
import { StockHistoryPage } from './StockHistoryPage';
import { ImportPage } from './ImportPage';
import { SuppliersPage } from './SuppliersPage';

type Page = 'dashboard' | 'products' | 'new-order' | 'orders' | 'ai-intake' | 'messages' | 'history' | 'imports' | 'suppliers' | 'admin' | 'operations' | 'settings';
const colors = ['#6965e9','#45b6a0','#e9b76b','#7d9cdc','#c288cc'];
function ProductIcon({category}:{category:string}) {
 const Icon = category==='Chargers'?Zap:category==='Cables'?Cable:category==='Cases'?Smartphone:category==='Headphones'?Headphones:Package;
 return <span className={'product-icon '+category.toLowerCase()}><Icon strokeWidth={1.5}/></span>;
}
function Status({stock}:{stock:number}) {return <span className={'badge '+(stock===0?'red':stock<=5?'amber':'green')}><span className="dot"/>{stockState(stock)}</span>;}

function LoginGate({onLogin}:{onLogin:(session:AuthSession)=>void}) {
 const [entry,setEntry]=useState<'choose'|'team'>(()=>location.hash==='#team'?'team':'choose');
 const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [ownerName,setOwnerName]=useState(''); const [needsSetup,setNeedsSetup]=useState<boolean|null>(null); const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
 useEffect(()=>{getSetupStatus().then(status=>setNeedsSetup(status.needs_owner_setup)).catch(()=>setNeedsSetup(false));},[]);
 const navigate=(next:'choose'|'team')=>{setEntry(next);setError('');setPassword('');history.replaceState(null,'',next==='choose'?location.pathname:('#'+next));};
 const submit=async(event:FormEvent)=>{event.preventDefault();setBusy(true);setError('');try{const session=needsSetup?await setupOwner(ownerName,email,password):await login(email,password);storeSession(session);onLogin(session);}catch(reason){const message=reason instanceof Error?reason.message:'Sign in failed.';setError(message);}finally{setBusy(false);}};
 return <main className="auth-page"><div className="auth-layout">
  <section className="auth-story"><a className="auth-brand" href="#"><span className="auth-brand-icon"><Boxes size={22}/></span>orderdesk<span>AI</span></a><div className="auth-story-copy"><div className="auth-kicker"><span/> WHOLESALE, IN GOOD ORDER</div><h1>Less chasing.<br/><em>More moving.</em></h1><p>One calm workspace for your catalog, incoming orders, and the people who keep them moving.</p><div className="auth-visual" aria-hidden="true"><div className="auth-orbit orbit-one"/><div className="auth-orbit orbit-two"/><div className="auth-float-card card-catalog"><span className="auth-visual-icon purple"><Boxes size={17}/></span><span><strong>Catalog in sync</strong><small>Products · stock · pricing</small></span><Check size={16} className="auth-check"/></div><div className="auth-float-card card-order"><span className="auth-visual-icon mint"><ClipboardList size={17}/></span><span><strong>Order ready to review</strong><small>Human checked · 3 items</small></span><span className="auth-order-dot"/></div><div className="auth-center-mark"><Building2 size={35}/></div></div></div><div className="auth-story-foot"><span>BUILT FOR YOUR TEAM</span><span>AI suggests. People decide.</span></div></section>
  <section className="auth-main"><div className="auth-main-inner">
   <div className="auth-topline"><span className="auth-secure"><LockKeyhole size={14}/> SECURE WORKSPACE</span><span>One desk, the right access.</span></div>
   {entry==='choose'&&<><div className="auth-heading"><div className="eyebrow">WELCOME TO ORDERDESK</div><h2>Ready to manage your shop?</h2><p>Sign in to manage products, customer requests, stock, and daily operations.</p></div><div className="entry-cards"><button className="entry-card entry-team" onClick={()=>navigate('team')}><span className="entry-icon team-icon"><Building2 size={21}/></span><span className="entry-card-copy"><small>TEAM ACCESS</small><strong>Team workspace</strong><span>For admins and staff managing catalog, requests, and orders.</span></span><ArrowRight size={18} className="entry-arrow"/><span className="entry-status ready">ADMIN / STAFF</span></button></div><div className="auth-footnote"><ShieldCheck size={16}/><span>Customer requests arrive through your connected message channels.</span></div></>}
   {entry==='team'&&<><button className="auth-back" onClick={()=>navigate('choose')}><ArrowLeft size={15}/> All workspaces</button><div className="auth-heading"><div className="eyebrow">TEAM WORKSPACE</div><h2>{needsSetup?'Set up your owner account.':'Good to have you back.'}</h2><p>{needsSetup?'Create the first secure account for this shop. You can add staff afterwards.':'Sign in with your admin or staff account.'}</p></div>{needsSetup===null?<p className="auth-form-note">Checking account setup...</p>:<form className="auth-form" onSubmit={submit}>{needsSetup&&<label>Your name<input autoComplete="name" value={ownerName} onChange={event=>setOwnerName(event.target.value)} required/></label>}<label>Email address<input autoComplete="username" type="email" value={email} onChange={event=>setEmail(event.target.value)} required/></label><label>Password<input autoComplete={needsSetup?'new-password':'current-password'} type="password" minLength={needsSetup?12:8} value={password} onChange={event=>setPassword(event.target.value)} required/></label>{needsSetup&&<small className="auth-form-note">Use at least 12 characters. This password is stored securely in the shop database.</small>}{error&&<p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" disabled={busy}>{busy?(needsSetup?'Creating account...':'Signing in...'):(needsSetup?'Create owner account':'Sign in to team workspace')}<ArrowRight size={17}/></button></form>}<div className="auth-form-note"><LockKeyhole size={14}/> Admins manage the catalog. Staff manage orders.</div></>}
   <div className="auth-main-footer"><span>AI Order Desk</span><span>Private by design</span></div>
  </div></section>
 </div></main>;
}

export default function App(){
 const [session,setSession]=useState<AuthSession|null>(()=>readSession());
 const [page,setPage]=useState<Page>((['dashboard','products','new-order','orders','ai-intake','messages','history','imports','suppliers','admin','operations','settings'].includes(location.hash.slice(1))?location.hash.slice(1):'dashboard') as Page);
 const [products,setProducts]=useState<Product[]>([]);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [refresh,setRefresh]=useState(0);
 const [updated,setUpdated]=useState<Date>();
 const [query,setQuery]=useState('');
 const [category,setCategory]=useState('All products');
 const [stock,setStock]=useState('All stock');
 const [sort,setSort]=useState('name');
 const [current,setCurrent]=useState(1);
 const [mobile,setMobile]=useState(false);
 const [selected,setSelected]=useState<Product|null>(null);
 const [orderRefresh,setOrderRefresh]=useState(0); const [messageDraft,setMessageDraft]=useState<{product_id:number;quantity:number}[]>([]);
 const dialog=useRef<HTMLDialogElement>(null);
 const searchRef=useRef<HTMLInputElement>(null);
 useEffect(()=>{const listener=()=>setPage((['dashboard','products','new-order','orders','ai-intake','messages','history','imports','suppliers','admin','operations','settings'].includes(location.hash.slice(1))?location.hash.slice(1):'dashboard') as Page);window.addEventListener('hashchange',listener);return()=>window.removeEventListener('hashchange',listener);},[]);
 useEffect(()=>{
  if(!session){setProducts([]);setLoading(false);setError('');return;}
  let disposed=false;
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),15000);
  setLoading(true);setError('');
  getProducts(controller.signal).then(items=>{if(!disposed){setProducts(items);setUpdated(new Date());}}).catch((reason)=>{
   if(disposed) return;
   const message=reason instanceof Error?reason.message:'';
   if(message.includes('Sign in is required')||message.includes('session is invalid')||message.includes('account is no longer active')){storeSession(null);setSession(null);setProducts([]);return;}
   if(!controller.signal.aborted) setError('We could not reach your catalog. Make sure FastAPI is running on port 8000.');
   else setError('The catalog request timed out. Check your backend connection and retry.');
  }).finally(()=>{clearTimeout(timeout);if(!disposed)setLoading(false);});
  return()=>{disposed=true;clearTimeout(timeout);controller.abort();};
 },[refresh,session?.token]);
 useEffect(()=>{setCurrent(1);},[query,category,stock,sort]);
 useEffect(()=>{if(selected) dialog.current?.showModal();},[selected]);
 const categories=useMemo(()=>[...new Set(products.map(p=>p.category))].sort(),[products]);
 const totals=useMemo(()=>({
  units:products.reduce((n,p)=>n+p.stock,0),
  value:products.reduce((n,p)=>n+priceCents(p.price)*p.stock,0),
  low:products.filter(p=>p.stock>0&&p.stock<=5).length,
  out:products.filter(p=>p.stock===0).length
 }),[products]);
 const filtered=useMemo(()=>products.filter(p=>
  (category==='All products'||p.category===category)&&
  (stock==='All stock'||(stock==='Needs attention'?p.stock<=5:stockState(p.stock)===stock))&&
  [p.sku,p.name,p.category].some(value=>value.toLowerCase().includes(query.toLowerCase().trim()))
 ).sort((a,b)=>sort==='price-up'?priceCents(a.price)-priceCents(b.price):sort==='price-down'?priceCents(b.price)-priceCents(a.price):sort==='stock'?a.stock-b.stock:a.name.localeCompare(b.name)),[products,category,stock,query,sort]);
 const pages=Math.max(1,Math.ceil(filtered.length/10));
 const visiblePage=Math.min(current,pages);
 const rows=filtered.slice((visiblePage-1)*10,visiblePage*10);
 const attention=products.filter(p=>p.stock<=5).sort((a,b)=>a.stock-b.stock);
 const go=(next:Page)=>{location.hash=next;setPage(next);setMobile(false);};
 const showAttention=()=>{setQuery('');setCategory('All products');setStock('Needs attention');go('products');};
 const reset=()=>{setQuery('');setCategory('All products');setStock('All stock');setSort('name');};
 const count=(n:number)=>loading||error?'—':n.toLocaleString();
 if(!session)return <LoginGate onLogin={setSession}/>;
 const logout=()=>{storeSession(null);setSession(null);setProducts([]);setPage('dashboard');location.hash='dashboard';};
 return <div className="app-shell">
  <a className="skip-link" href="#main-content">Skip to content</a>
  {mobile&&<button className="scrim" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
  <aside className={'sidebar '+(mobile?'open':'')}>
   <a className="brand" href="#dashboard" onClick={()=>go('dashboard')}><span className="brand-mark"><Boxes size={24}/></span><span>orderdesk<span className="brand-ai">AI</span></span></a>
   <div className="workspace"><span className="store-icon"><Smartphone size={21}/></span><div><strong>Mobile & more</strong><small>Demo workspace</small></div><span className="workspace-dot"/></div>
   <div className="nav-caption">WORKSPACE</div>
   <nav aria-label="Main navigation">
    <a href="#dashboard" aria-current={page==='dashboard'?'page':undefined} className={page==='dashboard'?'active':''} onClick={()=>go('dashboard')}><LayoutDashboard size={19}/>Overview</a>
    <a href="#new-order" aria-current={page==='new-order'?'page':undefined} className={page==='new-order'?'active':''} onClick={()=>go('new-order')}><Plus size={19}/>New order</a>
    <a href="#orders" aria-current={page==='orders'?'page':undefined} className={page==='orders'?'active':''} onClick={()=>go('orders')}><ClipboardList size={19}/>Orders</a>
    <a href="#products" aria-current={page==='products'?'page':undefined} className={page==='products'?'active':''} onClick={()=>go('products')}><Package size={19}/>Products<span className="nav-count">{count(products.length)}</span></a>
    <a href="#messages" aria-current={page==='messages'?'page':undefined} className={page==='messages'?'active':''} onClick={()=>go('messages')}><MessageCircle size={19}/>Messages</a>
    {session.role==='admin'&&<a href="#imports" aria-current={page==='imports'?'page':undefined} className={page==='imports'?'active':''} onClick={()=>go('imports')}><FileUp size={19}/>CSV import</a>}
    {session.role==='admin'&&<a href="#suppliers" aria-current={page==='suppliers'?'page':undefined} className={page==='suppliers'?'active':''} onClick={()=>go('suppliers')}><Building2 size={19}/>Suppliers</a>}
    {session.role==='admin'&&<a href="#history" aria-current={page==='history'?'page':undefined} className={page==='history'?'active':''} onClick={()=>go('history')}><History size={19}/>Stock history</a>}
    {session.role==='admin'&&<a href="#operations" aria-current={page==='operations'?'page':undefined} className={page==='operations'?'active':''} onClick={()=>go('operations')}><TrendingUp size={19}/>Operations</a>}
    {session.role==='admin'&&<a href="#settings" aria-current={page==='settings'?'page':undefined} className={page==='settings'?'active':''} onClick={()=>go('settings')}><SlidersHorizontal size={19}/>Settings</a>}
    {session.role==='admin'&&<a href="#admin" aria-current={page==='admin'?'page':undefined} className={page==='admin'?'active':''} onClick={()=>go('admin')}><ShieldCheck size={19}/>Admin</a>}
   </nav>
   <div className="sidebar-bottom"><div className="side-note"><Sparkles size={20}/><strong>A smarter way to work.</strong><p>Your catalog is the first step.<br/>AI-assisted orders are next.</p><span className="phase-tag">BUILDING THE FOUNDATION</span></div>
   <div className="profile"><span className="avatar">SO</span><div><strong>Shop owner</strong><small>Local demo</small></div><ShieldCheck size={18}/></div></div>
  </aside>
  <div className="main-shell">
   <header className="topbar"><div className="breadcrumbs"><button className="icon-button mobile-toggle" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu/></button><span>Workspace</span><ChevronRight size={14}/><strong>{{dashboard:'Overview',products:'Products','new-order':'New order','ai-intake':'AI intake',messages:'Messages',history:'Stock history',imports:'CSV import',suppliers:'Suppliers',orders:'Orders',admin:'Admin',operations:'Operations',settings:'Settings'}[page]}</strong></div><div className="topbar-right"><span className="demo-pill">{session.role.toUpperCase()}</span><span className={'connection '+(error?'offline':'')}><span className="dot"/>{loading?'Connecting':error?'Disconnected':'Catalog connected'}</span><span className="user-email">{session.email}</span><button className="admin-signout" onClick={logout}><LogOut size={15}/>Sign out</button></div></header>
   <main id="main-content">
    <div className="page-heading"><div><div className="eyebrow">{{dashboard:'YOUR BUSINESS, AT A GLANCE',products:'A PLACE FOR EVERY PRODUCT','new-order':'TURN REQUESTS INTO ACTION','ai-intake':'MESSAGE TO DRAFT',messages:'MESSAGE INBOX',history:'INVENTORY AUDIT',imports:'CATALOG IMPORT',suppliers:'SUPPLIER DIRECTORY',orders:'EVERY DRAFT, IN ONE PLACE',admin:'OWNER ACCESS',operations:'DAILY OPERATIONS',settings:'WHATSAPP SETTINGS'}[page]}</div><h1>{{dashboard:'A clearer view of your shop.',products:'Your product catalog.','new-order':'Create a manual order.','ai-intake':'Let the assistant read the request.',messages:'Review incoming messages.',history:'Track every stock change.',imports:'Preview catalog updates safely.',suppliers:'Manage supplier contacts.',orders:'Keep orders moving.',admin:'Manage your catalog.',operations:'Review today’s decisions.',settings:'Manage customer replies.'}[page]}</h1><p>{{dashboard:'Keep an eye on your inventory. Know what needs attention.',products:'Find the right product, check availability, and keep things moving.','new-order':'Build the workflow the AI will later help complete.','ai-intake':'Structured suggestions first. Your approval before any business action.',messages:'Read incoming channel messages and send each request to staff review.',history:'View the audit trail created when approved orders are dispatched.',imports:'Upload a product CSV, review each row, then confirm the catalog update.',suppliers:'Keep supplier contacts and delivery times ready for manual restock follow-up.',orders:'Review the drafts your team has started.',admin:'Sign in to add or update shop products.',operations:'Review stock suggestions before placing any supplier order.',settings:'Change the business number and customer-facing WhatsApp introduction.'}[page]}</p></div><button className="button secondary" disabled={loading} onClick={()=>setRefresh(v=>v+1)}><RefreshCw size={16} className={loading?'spin':''}/>{loading?'Refreshing…':'Refresh catalog'}</button></div>
    {error?<div role="alert" className="error-state"><TriangleAlert/><div><strong>Your catalog is temporarily unavailable</strong><p>{error}</p></div><button className="button secondary" onClick={()=>setRefresh(v=>v+1)}>Try again</button></div>:<>
    {page==='dashboard'&&<section className="stats" aria-label="Inventory summary">
     <article className="stat"><div className="stat-top"><span>Total products</span><span className="stat-icon violet"><Package size={19}/></span></div><strong>{count(products.length)}</strong><small>Across {count(categories.length)} categories</small></article>
     <article className="stat"><div className="stat-top"><span>Units on hand</span><span className="stat-icon teal"><Boxes size={19}/></span></div><strong>{count(totals.units)}</strong><small>Current physical inventory</small></article>
     <article className="stat"><div className="stat-top"><span>Retail stock value</span><span className="stat-icon blue"><Wallet size={19}/></span></div><strong>{loading?'—':money(totals.value)}</strong><small>At catalog prices · USD</small></article>
     <button className="stat attention-stat" onClick={showAttention} disabled={loading}><div className="stat-top"><span>Needs attention</span><span className="stat-icon orange"><TriangleAlert size={19}/></span></div><strong>{count(totals.low+totals.out)}<ArrowUpRight size={23}/></strong><small>{count(totals.low)} low stock <span>·</span> {count(totals.out)} out of stock</small></button>
    </section>}
    {loading?<div className="panel skeleton-panel" role="status" aria-label="Loading catalog"><div className="skeleton"/><div className="skeleton"/><div className="skeleton"/><p>Getting your catalog ready…</p></div>  :page==='dashboard'?<>
     <div className="dashboard-grid">
      <section className="panel category-panel"><div className="section-heading"><div><h2>Your catalog, by category</h2><p>A balanced view of what you carry.</p></div><span className="subtle-label">PRODUCT MIX</span></div>
       <div className="category-content"><div className="donut" role="img" aria-label={categories.map(c=>c+': '+products.filter(p=>p.category===c).length+' products').join(', ')||'Empty catalog'} style={{background:products.length?'conic-gradient('+categories.map((c,i)=>{const start=categories.slice(0,i).reduce((n,cat)=>n+products.filter(p=>p.category===cat).length,0)/products.length*100;const end=start+products.filter(p=>p.category===c).length/products.length*100;return colors[i%colors.length]+' '+start+'% '+end+'%';}).join(',')+')':'#eef0f5'}}><div><strong>{products.length}</strong><span>products</span></div></div>
       <div className="category-legend">{categories.map((c,i)=><button key={c} onClick={()=>{reset();setCategory(c);go('products');}}><span className="legend-dot" style={{background:colors[i%colors.length]}}/><span>{c}</span><strong>{products.filter(p=>p.category===c).length}</strong><ChevronRight size={14}/></button>)}{!categories.length&&<p>No products yet.</p>}</div></div>
       <div className="panel-foot"><ShieldCheck size={16}/>Calculated directly from your catalog.</div>
      </section>
      <section className="feature-card"><span className="feature-tag"><span className="dot"/>YOUR INVENTORY HUB</span><h2>Less searching.<br/>More clarity.</h2><p>Every SKU, price, and stock level.<br/>One organized place to find it all.</p><button className="button white" onClick={()=>{reset();go('products');}}>Explore products<ArrowRight size={17}/></button><div className="box-art" aria-hidden="true"><div className="art-orbit"/><div className="art-tile back"><Cable/></div><div className="art-tile front"><Headphones/></div><div className="art-check"><Check size={18}/></div></div></section>
     </div>
     <section className="panel attention-panel"><div className="section-heading"><div><h2><span className="small-alert"><TriangleAlert size={17}/></span>A little attention goes a long way</h2><p>Products with 5 or fewer units on hand.</p></div><button className="text-button" onClick={showAttention}>View all {attention.length}<ArrowRight size={16}/></button></div>
      {attention.length?<div className="attention-list">{attention.slice(0,4).map(p=><button key={p.id} className="attention-item" onClick={()=>setSelected(p)}><ProductIcon category={p.category}/><div><strong>{p.name}</strong><small>{p.sku}</small></div><Status stock={p.stock}/><ChevronRight size={16}/></button>)}</div>:<div className="empty-inline"><ShieldCheck/> {products.length?'All products have more than 5 units on hand.':'Your catalog is empty. Add products through the API to get started.'}</div>}
     </section>
    </>:page==='suppliers'&&session.role==='admin'?<SuppliersPage/>:page==='imports'&&session.role==='admin'?<ImportPage onImported={()=>setRefresh(value=>value+1)}/>:page==='history'&&session.role==='admin'?<StockHistoryPage/>:page==='messages'?<MessageInboxPage products={products} onCreateDraft={lines=>{setMessageDraft(lines);go('new-order');}}/>:page==='new-order'?<OrderWorkspace products={products} initialLines={messageDraft} onOrderSaved={()=>setOrderRefresh(value=>value+1)}/>:page==='ai-intake'?<AiIntake products={products} onSaved={()=>setOrderRefresh(value=>value+1)}/>:page==='orders'?<OrdersPage refreshToken={orderRefresh} onOrderChanged={()=>{setOrderRefresh(value=>value+1);setRefresh(value=>value+1);}}/>:page==='settings'&&session.role==='admin'?<SettingsPage/>:page==='operations'&&session.role==='admin'?<OperationsPage onSessionReset={logout}/>:page==='admin'&&session.role==='admin'?<AdminPage products={products} onChanged={()=>setRefresh(value=>value+1)} onLogout={logout}/>:<section className="panel catalog">
     <div className="section-heading"><div><h2>All the essentials. Organized.<span className="number-tag">{products.length}</span></h2><p>Browse your inventory by name, SKU, or category.</p></div><Package size={23} className="muted"/></div>
     <div className="catalog-controls"><div className="search-field"><Search size={18}/><input ref={searchRef} aria-label="Search products" placeholder="Search products or SKU…" value={query} onChange={e=>setQuery(e.target.value)}/>{query&&<button aria-label="Clear search" onClick={()=>{setQuery('');searchRef.current?.focus();}}><X size={16}/></button>}</div><label className="select-wrap"><SlidersHorizontal size={16}/><select aria-label="Filter by stock" value={stock} onChange={e=>setStock(e.target.value)}>{['All stock','In stock','Low stock','Out of stock','Needs attention'].map(s=><option key={s}>{s}</option>)}</select></label><label className="select-wrap"><ArrowDown size={15}/><select aria-label="Sort products" value={sort} onChange={e=>setSort(e.target.value)}><option value="name">Name: A–Z</option><option value="price-up">Price: low to high</option><option value="price-down">Price: high to low</option><option value="stock">Stock: low to high</option></select></label></div>
     <div className="category-tabs" aria-label="Category filters">{['All products',...categories].map(c=><button aria-pressed={category===c} key={c} className={category===c?'selected':''} onClick={()=>setCategory(c)}>{c}<span>{c==='All products'?products.length:products.filter(p=>p.category===c).length}</span></button>)}</div>
     <div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>SKU</th><th>CATEGORY</th><th className="numeric">UNIT PRICE</th><th className="numeric">ON HAND</th><th>AVAILABILITY</th><th><span className="sr-only">Details</span></th></tr></thead><tbody>{rows.map(p=><tr key={p.id}><td><button className="product-name" onClick={()=>setSelected(p)}><ProductIcon category={p.category}/><span>{p.name}</span></button></td><td className="sku">{p.sku}</td><td><span className="category-label">{p.category}</span></td><td className="numeric price">{money(priceCents(p.price))}</td><td className="numeric stock-count">{p.stock}<span> units</span></td><td><Status stock={p.stock}/></td><td><button className="icon-button" aria-label={'View '+p.name} onClick={()=>setSelected(p)}><ArrowUpRight size={17}/></button></td></tr>)}</tbody></table></div>
     {!rows.length&&<div className="empty"><Search size={30}/><h3>{products.length?'No matching products':'Your catalog is empty'}</h3><p>{products.length?'Try another search or clear your filters.':'Add sample products to start exploring your inventory.'}</p>{products.length>0&&<button className="button secondary" onClick={reset}>Clear filters</button>}</div>}
     <div className="pagination"><span aria-live="polite">{filtered.length?'Showing '+((visiblePage-1)*10+1)+'–'+Math.min(visiblePage*10,filtered.length)+' of '+filtered.length+' products':'0 products'}</span><div><button aria-label="Previous page" disabled={visiblePage===1} onClick={()=>setCurrent(visiblePage-1)}><ChevronLeft size={17}/></button><span>Page {visiblePage} of {pages}</span><button aria-label="Next page" disabled={visiblePage===pages} onClick={()=>setCurrent(visiblePage+1)}><ChevronRight size={17}/></button></div></div>
    </section>}
    </>}
    <footer><span><span className="footer-brand">orderdesk</span> A little more organized. A lot more possible.</span><span><CircleHelp size={14}/>Demo prices in USD{updated&&!error?' · Updated '+updated.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):''}</span></footer>
   </main>
  </div>
  <dialog ref={dialog} onClose={()=>setSelected(null)} onClick={event=>{if(event.target===dialog.current)dialog.current.close();}} className="product-dialog">
   {selected&&<><div className="dialog-top"><span className="eyebrow">PRODUCT DETAILS</span><button className="icon-button" aria-label="Close details" onClick={()=>dialog.current?.close()}><X/></button></div><ProductIcon category={selected.category}/><h2>{selected.name}</h2><p className="sku">{selected.sku}</p><Status stock={selected.stock}/><dl><div><dt>Category</dt><dd>{selected.category}</dd></div><div><dt>Unit price · USD</dt><dd>{money(priceCents(selected.price))}</dd></div><div><dt>Units on hand</dt><dd>{selected.stock}</dd></div><div><dt>Retail stock value</dt><dd>{money(priceCents(selected.price)*selected.stock)}</dd></div></dl><p className="detail-note">Stock status: out of stock at 0 units, low stock at 1–5 units.</p><button className="button primary full" onClick={()=>dialog.current?.close()}>Done</button></>}
  </dialog>
 </div>;
}



