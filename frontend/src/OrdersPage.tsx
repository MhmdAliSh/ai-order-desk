import { useEffect, useState } from 'react';
import { ClipboardList } from 'lucide-react';
import { getOrders, money, priceCents, type Order } from './api';

const statusLabel: Record<Order['status'], string> = {draft:'Draft', approved:'Reserved', dispatched:'Dispatched', cancelled:'Cancelled'};
export function OrdersPage({ refreshToken }: { refreshToken: number; onOrderChanged: () => void }) {
 const [orders,setOrders]=useState<Order[]>([]);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 useEffect(()=>{const c=new AbortController();setLoading(true);setError('');getOrders(c.signal).then(setOrders).catch((e:Error)=>{if(e.name!=='AbortError'&&!c.signal.aborted)setError(e.message)}).finally(()=>{if(!c.signal.aborted)setLoading(false)});return()=>c.abort()},[refreshToken]);
 return <section className="panel orders-page"><div className="section-heading"><div><div className="eyebrow">ORDER HISTORY</div><h2>Order summary</h2><p>Order confirmation and dispatch happen from the New Order screen.</p></div><ClipboardList className="muted"/></div>{error&&<div className="order-banner error">{error}</div>}{loading?<div className="empty">Loading orders…</div>:<div className="table-scroll"><table><thead><tr><th>ORDER</th><th>CUSTOMER</th><th>ITEMS</th><th>STATUS</th><th className="numeric">TOTAL</th><th>CREATED</th></tr></thead><tbody>{orders.map(order=><tr key={order.id}><td className="sku">ORDER-{String(order.id).padStart(4,'0')}</td><td><strong>{order.customer.name}</strong><br/><span className="table-subtle">{order.customer.contact_name}</span></td><td>{order.items.length} item{order.items.length===1?'':'s'}</td><td><span className={'badge order-'+order.status}>{statusLabel[order.status]}</span></td><td className="numeric price">{money(priceCents(order.total))}</td><td className="table-subtle">{new Date(order.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div>}</section>;
}
