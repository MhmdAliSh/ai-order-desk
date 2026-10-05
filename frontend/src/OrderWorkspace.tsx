import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Minus, Plus, Search, Send, Trash2, TriangleAlert } from 'lucide-react';
import { changeOrderStatus, createOrder, getCustomers, getPhoneUnits, money, priceCents, type Customer, type PhoneUnit, type Product } from './api';
import { BarcodeScanner } from './BarcodeScanner';

type Line = { product: Product; quantity: number; phoneUnitId?: number };

export function OrderWorkspace({ products, onOrderSaved, initialLines=[] }: { products: Product[]; onOrderSaved: () => void; initialLines?: {product_id:number;quantity:number}[] }) {
 const [customers, setCustomers] = useState<Customer[]>([]);
 const [customerId, setCustomerId] = useState('');
 const [query, setQuery] = useState('');
 const [lines, setLines] = useState<Line[]>([]);
 const [loadingCustomers, setLoadingCustomers] = useState(true);
 const [saving, setSaving] = useState(false);
 const [error, setError] = useState('');
 const [success, setSuccess] = useState(''); const [savedOrder,setSavedOrder]=useState<{id:number;status:'draft'|'approved'|'dispatched'|'cancelled'}>();
 const [phoneUnits,setPhoneUnits]=useState<PhoneUnit[]>([]);
 const [scannerOpen,setScannerOpen]=useState(false);
 useEffect(() => {
  const controller = new AbortController();
  getCustomers(controller.signal).then(setCustomers).catch((reason: Error) => { if(reason.name!=='AbortError'&&!controller.signal.aborted)setError(reason.message); }).finally(() => { if(!controller.signal.aborted)setLoadingCustomers(false); });
  return () => controller.abort();
 }, []);
 useEffect(()=>{if(initialLines.length)setLines(initialLines.map(line=>{const product=products.find(item=>item.id===line.product_id);return product?{product,quantity:Math.min(product.stock,line.quantity)}:null}).filter((line):line is Line=>line!==null));},[initialLines,products]);
 useEffect(()=>{getPhoneUnits(new AbortController().signal).then(setPhoneUnits).catch(()=>setPhoneUnits([]));},[]);
 const matches = useMemo(() => products.filter(product => product.stock > 0 && [product.name, product.sku, product.barcode || ''].some(value => value.toLowerCase().includes(query.toLowerCase().trim()))).slice(0, 8), [products, query]);
 const total = lines.reduce((sum, line) => sum + priceCents(line.product.price) * line.quantity, 0);
 const add = (product: Product) => { setLines(previous => previous.some(line => line.product.id === product.id) ? previous : [...previous, { product, quantity: 1 }]); setQuery(''); setSuccess(''); };
 const updateQuantity = (productId: number, quantity: number) => setLines(previous => previous.map(line => line.product.id === productId ? { ...line, quantity: Math.max(1, Math.min(line.product.stock, quantity)) } : line));
 const save = async () => {
  setError(''); setSuccess('');
  if (!customerId) return setError('Choose a customer before saving the draft.');
  if (!lines.length) return setError('Add at least one product to the order.');
  if (lines.some(line=>line.product.category==='Phones'&&!line.phoneUnitId)) return setError('Choose the exact phone unit and IMEI before saving.');
  setSaving(true);
  try {
   const order = await createOrder(Number(customerId), lines.map(line => ({ product_id: line.product.id, quantity: line.quantity, ...(line.phoneUnitId?{phone_unit_id:line.phoneUnitId}:{}) })));
   setSuccess(`Draft #${order.id} saved for ${order.customer.name}.`); setSavedOrder({id:order.id,status:'draft'}); setLines([]); setCustomerId(''); onOrderSaved();
  } catch (reason) { setError(reason instanceof Error ? reason.message : 'The order draft could not be saved.'); } finally { setSaving(false); }
 };
 const progress=async(action:'approve'|'dispatch')=>{if(!savedOrder)return;setSaving(true);setError('');try{const updated=await changeOrderStatus(savedOrder.id,action);setSavedOrder({id:updated.id,status:updated.status});setSuccess(updated.message);onOrderSaved();}catch(reason){setError(reason instanceof Error?reason.message:'Order action could not be completed.');}finally{setSaving(false);}};
 return <section className="order-workspace">
  <div className="order-main panel">
   <div className="section-heading"><div><div className="eyebrow">START WITH A CLEAR DRAFT</div><h2>Build an order.</h2><p>Choose a customer, then add products from your catalog.</p></div></div>
   <div className="form-section"><label className="field-label">Customer<select aria-label="Customer" value={customerId} disabled={loadingCustomers} onChange={event => setCustomerId(event.target.value)}><option value="">{loadingCustomers ? 'Loading customers…' : 'Select a customer'}</option>{customers.map(customer => <option key={customer.id} value={customer.id}>{customer.name} · {customer.contact_name}</option>)}</select></label></div>
   <div className="form-section"><label className="field-label">Add products<div className="order-search"><Search size={18}/><input aria-label="Add product" placeholder="Search name, SKU, or scan/type barcode…" value={query} onChange={event => setQuery(event.target.value)}/></div><small>Hardware scanners enter the barcode here automatically.</small></label><button type="button" className="button secondary" onClick={()=>setScannerOpen(true)}>Scan barcode with camera</button>{scannerOpen&&<BarcodeScanner onDetected={barcode=>{setQuery(barcode);setScannerOpen(false);}} onClose={()=>setScannerOpen(false)}/>} {query && <div className="product-picker">{matches.map(product => <button key={product.id} onClick={() => add(product)}><span><strong>{product.name}</strong><small>{product.sku} · {product.stock} available</small></span><span>{money(priceCents(product.price))}</span><Plus size={17}/></button>)}{!matches.length && <p>No in-stock products match that search.</p>}</div>}</div>
  <div className="order-lines"><div className="line-header"><span>PRODUCT</span><span>QUANTITY</span><span>UNIT PRICE</span><span>TOTAL</span><span/></div>{lines.map(line => <div className="order-line" key={line.product.id}><div><strong>{line.product.name}</strong><small>{line.product.sku} · {line.product.stock} available</small>{line.product.category==='Phones'&&<select aria-label={`Phone unit for ${line.product.name}`} value={line.phoneUnitId||''} onChange={event=>setLines(previous=>previous.map(item=>item.product.id===line.product.id?{...item,phoneUnitId:Number(event.target.value)||undefined,quantity:1}:item))}><option value="">Choose IMEI</option>{phoneUnits.filter(unit=>unit.product_id===line.product.id&&unit.status==='available').map(unit=><option key={unit.id} value={unit.id}>{unit.imei} · {unit.colour} · {unit.storage}</option>)}</select>}</div><div className="quantity"><button aria-label={`Decrease ${line.product.name}`} onClick={() => updateQuantity(line.product.id, line.quantity - 1)}><Minus size={14}/></button><input aria-label={`Quantity for ${line.product.name}`} type="number" min="1" max={line.product.category==='Phones'?1:line.product.stock} value={line.quantity} onChange={event => updateQuantity(line.product.id, Number(event.target.value))}/><button aria-label={`Increase ${line.product.name}`} disabled={line.quantity >= (line.product.category==='Phones'?1:line.product.stock)} onClick={() => updateQuantity(line.product.id, line.quantity + 1)}><Plus size={14}/></button></div><span>{money(priceCents(line.product.price))}</span><strong>{money(priceCents(line.product.price) * line.quantity)}</strong><button className="icon-button delete" aria-label={`Remove ${line.product.name}`} onClick={() => setLines(previous => previous.filter(item => item.product.id !== line.product.id))}><Trash2 size={17}/></button></div>)}{!lines.length && <div className="order-empty"><Search size={25}/><strong>Your draft is empty</strong><span>Search the catalog above to add your first product.</span></div>}</div>
  </div>
  <aside className="order-summary panel"><div className="eyebrow">DRAFT SUMMARY</div><h2>Ready when you are.</h2><div className="summary-items"><span>{lines.length} product{lines.length === 1 ? '' : 's'}</span><strong>{money(total)}</strong></div><div className="summary-rule"/><p>Prices are taken from the product catalog. Stock is checked when you save the draft.</p>{error && <div role="alert" className="order-message error"><TriangleAlert size={17}/>{error}</div>}{success && <div role="status" className="order-message success"><CheckCircle2 size={17}/>{success}</div>}{savedOrder?.status==='draft'&&<button className="button secondary full" disabled={saving} onClick={()=>progress('approve')}>Confirm order</button>}{savedOrder?.status==='approved'&&<button className="button primary full" disabled={saving} onClick={()=>progress('dispatch')}><Send size={15}/>Confirm dispatch</button>}{savedOrder?.status==='dispatched'&&<p className="summary-note">Order dispatched and stock updated.</p>}<button className="button primary full" disabled={saving || loadingCustomers} onClick={save}>{saving ? 'Saving draft…' : 'Save draft'}</button><small className="summary-note">A draft does not reserve or deduct stock.</small></aside>
 </section>;
}


