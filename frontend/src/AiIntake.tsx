import { useEffect, useState } from 'react';
import { CheckCircle2, Sparkles, TriangleAlert, X } from 'lucide-react';
import { analyzeMessage, createOrder, getCustomers, money, priceCents, type Customer, type Intake, type IntakeItem, type Product } from './api';

export function AiIntake({ products, onSaved }: { products: Product[]; onSaved: () => void }) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState('');
  const [message, setMessage] = useState('');
  const [intake, setIntake] = useState<Intake>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getCustomers(controller.signal).then(setCustomers).catch((reason: Error) => setError(reason.message));
    const inboxMessage=sessionStorage.getItem('orderdesk-inbox-message');
    if(inboxMessage){setMessage(inboxMessage);sessionStorage.removeItem('orderdesk-inbox-message');}
    return () => controller.abort();
  }, []);

  const analyze = async () => {
    setError(''); setNotice(''); setBusy(true);
    try { setIntake(await analyzeMessage(message)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The message could not be analyzed.'); }
    finally { setBusy(false); }
  };

  const updateItem = (index: number, updates: Partial<IntakeItem>) => setIntake(current => {
    if (!current) return current;
    return { ...current, items: current.items.map((item, itemIndex) => itemIndex === index ? { ...item, ...updates } : item) };
  });

  const chooseProduct = (index: number, productId: number) => {
    const product = products.find(candidate => candidate.id === productId);
    const item = intake?.items[index];
    if (!product || !item) return;
    const unavailable = item.quantity !== null && item.quantity > product.stock;
    updateItem(index, {
      suggested_product: { id: product.id, sku: product.sku, name: product.name, stock: product.stock },
      match_status: unavailable ? 'unavailable' : 'matched',
      evidence: unavailable ? `You selected this item. Requested ${item.quantity}; only ${product.stock} are on hand.` : 'Product selected and confirmed by staff.',
    });
  };

  const changeQuantity = (index: number, value: string) => {
    const quantity = value === '' ? null : Number(value);
    if (!Number.isInteger(quantity) && quantity !== null) return;
    const item = intake?.items[index];
    if (!item) return;
    const unavailable = item.suggested_product && quantity !== null && quantity > item.suggested_product.stock;
    updateItem(index, {
      quantity,
      match_status: unavailable ? 'unavailable' : item.suggested_product && quantity !== null ? 'matched' : 'needs_review',
      evidence: unavailable ? `Requested ${quantity}; only ${item.suggested_product!.stock} are on hand.` : item.suggested_product && quantity !== null ? 'Product and quantity confirmed by staff.' : 'Choose a product and enter a quantity.',
    });
  };

  const dismissItem = (index: number) => setIntake(current => current ? { ...current, items: current.items.filter((_, itemIndex) => itemIndex !== index) } : current);

  const isResolved = (item: IntakeItem) => item.suggested_product !== null && item.quantity !== null && item.quantity > 0 && item.quantity <= item.suggested_product.stock;
  const save = async () => {
    if (!customerId) return setError('Choose a customer before saving.');
    if (!intake) return;
    if (!intake.items.length) return setError('Add or analyze an item before saving this draft.');
    if (intake.items.some(item => !isResolved(item))) return setError('Choose an in-stock catalog product and quantity for every highlighted item before saving.');
    setBusy(true); setError('');
    try { const order = await createOrder(Number(customerId), intake.items.map(item => ({ product_id: item.suggested_product!.id, quantity: item.quantity! }))); setNotice(`Draft #${order.id} saved for ${order.customer.name}.`); onSaved(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The draft could not be saved.'); }
    finally { setBusy(false); }
  };

  const total = (intake?.items ?? []).reduce((sum, item) => {
    const product = products.find(candidate => candidate.id === item.suggested_product?.id);
    return sum + (product && item.quantity ? priceCents(product.price) * item.quantity : 0);
  }, 0);

  return <section className="ai-intake">
    <div className="panel intake-entry">
      <div className="section-heading"><div><div className="eyebrow">AI-ASSISTED INTAKE</div><h2>Paste a customer request.</h2><p>The assistant suggests structured items. You review every decision.</p></div><Sparkles className="muted" /></div>
      <div className="form-section"><label className="field-label">Customer<select aria-label="AI customer" value={customerId} onChange={event => setCustomerId(event.target.value)}><option value="">Select a customer</option>{customers.map(customer => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label></div>
      <div className="form-section"><label className="field-label">Customer message<textarea aria-label="Customer message" value={message} onChange={event => setMessage(event.target.value)} placeholder="Example: Please send 10 25W chargers and 8 USB-C cables." /></label><button className="button primary" disabled={!message.trim() || busy} onClick={analyze}>{busy ? 'Analyzing…' : 'Analyze message'}<Sparkles size={16} /></button></div>
    </div>
    {error && <div role="alert" className="order-banner error">{error}</div>}
    {notice && <div role="status" className="order-banner success"><CheckCircle2 size={16} />{notice}</div>}
    {intake && <section className="panel intake-results">
      <div className="section-heading"><div><h2>Review suggestions.</h2><p>{intake.mode === 'live' ? 'Live AI extracted the request. Catalog matching and stock validation remain in this app.' : 'Demo mode uses local structured extraction and catalog similarity matching.'}</p></div><span className="number-tag">{intake.items.length} items</span></div>
      <div className="intake-list">{intake.items.length ? intake.items.map((item, index) => <article key={index} className={'intake-item ' + item.match_status}>
        <div><span className="table-subtle">REQUESTED</span><strong>{item.quantity ?? '—'} × {item.requested_description}</strong><p>{item.evidence}</p></div>
        <div><span className="table-subtle">CONFIRM CATALOG ITEM</span><label className="intake-editor">Product<select aria-label={`Product for ${item.requested_description}`} value={item.suggested_product?.id ?? ''} onChange={event => chooseProduct(index, Number(event.target.value))}><option value="">Choose a product</option>{products.map(product => <option key={product.id} value={product.id}>{product.name} · {product.stock} in stock</option>)}</select></label><label className="intake-editor">Quantity<input aria-label={`Quantity for ${item.requested_description}`} min="1" type="number" value={item.quantity ?? ''} onChange={event => changeQuantity(index, event.target.value)} /></label><span className={'badge ' + (item.match_status === 'matched' ? 'green' : item.match_status === 'unavailable' ? 'red' : 'amber')}>{item.match_status === 'matched' ? 'Ready to save' : item.match_status === 'unavailable' ? 'Not enough stock' : 'Needs review'}</span></div>
        <button className="mini-icon dismiss-item" aria-label={`Dismiss ${item.requested_description}`} title="Dismiss item" onClick={() => dismissItem(index)}><X size={16}/></button>
      </article>) : <p className="empty-inline">All items were dismissed. Analyze another request to continue.</p>}</div>
      {intake.notes.map(note => <p className="intake-note" key={note}><TriangleAlert size={15} />{note}</p>)}
      <div className="intake-footer"><strong>{money(total)}</strong><button className="button primary" disabled={busy || !intake.items.length} onClick={save}>Save reviewed draft</button></div>
    </section>}
  </section>;
}
