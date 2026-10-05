export type Product = {id:number;sku:string;name:string;category:string;price:string;stock:number;barcode:string|null;imei:string|null};
export type PhoneUnit={id:number;product_id:number;imei:string;colour:string;storage:string;supplier_name:string|null;purchase_cost:string;warranty_status:string;status:'available'|'reserved'|'dispatched';created_at:string};
export type Customer = {id:number;name:string;contact_name:string;phone:string;email:string};
export type OrderItem = {id:number;product_id:number;sku:string;product_name:string;unit_price:string;quantity:number;line_total:string};
export type Order = {id:number;customer:Customer;status:'draft'|'approved'|'dispatched'|'cancelled';total:string;created_at:string;items:OrderItem[]};
export type Role = 'admin'|'staff';
export type AuthSession = {token:string;email:string;role:Role};
const sessionKey='orderdesk-session';
export function readSession(): AuthSession|null { try { const value=localStorage.getItem(sessionKey); return value?JSON.parse(value) as AuthSession:null; } catch { return null; } }
export function storeSession(session:AuthSession|null) { if(session)localStorage.setItem(sessionKey,JSON.stringify(session));else localStorage.removeItem(sessionKey); }
async function apiFetch(input:RequestInfo|URL,init:RequestInit={}) { const headers=new Headers(init.headers); const token=readSession()?.token; if(token)headers.set('Authorization','Bearer '+token); return fetch(input,{...init,headers}); }
export async function getProducts(signal:AbortSignal): Promise<Product[]> {
 const all:Product[]=[];
 for(let offset=0;;offset+=100){
  const response=await apiFetch('/api/products?limit=100&offset='+offset,{signal});
  if(!response.ok) { await requireOk(response,'The catalog could not be loaded. Check that your backend is running, then retry.'); }
  const page:Product[]=await response.json();
  all.push(...page);
  if(page.length<100) return all;
 }
}
export const priceCents=(price:string) => {const [whole,fraction='']=price.split('.');return Number(whole)*100+Number(fraction.padEnd(2,'0').slice(0,2));};
export const money=(cents:number) => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(cents/100);
export const stockState=(stock:number)=> stock===0?'Out of stock':stock<=5?'Low stock':'In stock';

async function requireOk(response: Response, fallback: string) {
 if(response.ok) return response;
 const body = await response.json().catch(() => null);
 const detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.message;
 throw new Error(detail || fallback);
}
export async function getCustomers(signal:AbortSignal): Promise<Customer[]> {
 return requireOk(await apiFetch('/api/customers',{signal}),'The customer list could not be loaded.').then(response=>response.json());
}
export async function getOrders(signal:AbortSignal): Promise<Order[]> {
 return requireOk(await apiFetch('/api/orders',{signal}),'The order history could not be loaded.').then(response=>response.json());
}
export async function createOrder(customerId:number,items:{product_id:number;quantity:number;phone_unit_id?:number}[]): Promise<Order> {
 return requireOk(await apiFetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_id:customerId,items})}),'The order draft could not be saved.').then(response=>response.json());
}
export async function changeOrderStatus(orderId:number, action:'approve'|'dispatch'|'cancel'): Promise<Order & {message:string}> {
 return requireOk(await apiFetch(`/api/orders/${orderId}/${action}`,{method:'POST'}),'The order action could not be completed.').then(response=>response.json());
}
export type IntakeItem = {requested_description:string;quantity:number|null;suggested_product:{id:number;sku:string;name:string;stock:number}|null;match_status:'matched'|'needs_review'|'unavailable';evidence:string};
export type Intake = {mode:'demo'|'live';items:IntakeItem[];notes:string[]};
export async function analyzeMessage(message:string): Promise<Intake> {
 return requireOk(await apiFetch('/api/order-intake/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})}),'The message could not be analyzed.').then(response=>response.json());
}
export async function login(email:string,password:string): Promise<AuthSession> {
 return requireOk(await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})}),'Login failed.').then(response=>response.json());
}
export async function getSetupStatus():Promise<{needs_owner_setup:boolean}>{return requireOk(await fetch('/api/auth/setup-status'),'Could not check account setup.').then(response=>response.json());}
export async function setupOwner(name:string,email:string,password:string):Promise<AuthSession>{return requireOk(await fetch('/api/auth/setup-owner',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,password})}),'Owner account could not be created.').then(response=>response.json());}
export async function saveProduct(product:Omit<Product,'id'|'imei'> & {imei?:string|null}, id?:number): Promise<Product> {
 return requireOk(await apiFetch(id?`/api/products/${id}`:'/api/products',{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(product)}),'Product could not be saved.').then(response=>response.json());
}
export async function getPhoneUnits(signal:AbortSignal):Promise<PhoneUnit[]>{return requireOk(await apiFetch('/api/phone-units',{signal}),'Phone units could not be loaded.').then(response=>response.json());}
export async function createPhoneUnit(unit:Omit<PhoneUnit,'id'|'status'|'created_at'>):Promise<PhoneUnit>{return requireOk(await apiFetch('/api/phone-units',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(unit)}),'Phone unit could not be saved.').then(response=>response.json());}
export async function saveCustomer(customer:Omit<Customer,'id'>,id?:number):Promise<Customer> {
 return requireOk(await apiFetch(id?`/api/customers/${id}`:'/api/customers',{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(customer)}),'Customer could not be saved.').then(response=>response.json());
}
export type RestockRecommendation={product_id:number;sku:string;name:string;stock:number;weekly_sales:number;reorder_quantity:number;reason:string};
export type DailyOperations={period_days:number;dispatched_orders:number;revenue:string;recommendations:RestockRecommendation[];report:string};
export async function getDailyOperations(signal:AbortSignal):Promise<DailyOperations>{return requireOk(await apiFetch('/api/operations/daily-summary',{signal}),'The daily operations summary could not be loaded.').then(response=>response.json());}
export type SavedDailyReport={id:number;report_date:string;report:string;created_at:string};
export async function getSavedDailyReports(signal:AbortSignal):Promise<SavedDailyReport[]>{return requireOk(await apiFetch('/api/operations/daily-reports',{signal}),'Saved reports could not be loaded.').then(response=>response.json());}
export async function runDailyReport():Promise<SavedDailyReport>{return requireOk(await apiFetch('/api/operations/daily-reports/run',{method:'POST'}),'The daily report could not be saved.').then(response=>response.json());}
export type IntegrationSettings={id:number;whatsapp_business_number:string;whatsapp_intro:string};
export async function getIntegrationSettings(signal:AbortSignal):Promise<IntegrationSettings>{return requireOk(await apiFetch('/api/settings/integrations',{signal}),'Settings could not be loaded.').then(response=>response.json());}
export async function saveIntegrationSettings(settings:Omit<IntegrationSettings,'id'>):Promise<IntegrationSettings>{return requireOk(await apiFetch('/api/settings/integrations',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)}),'Settings could not be saved.').then(response=>response.json());}

export type TeamUser={id:number;name:string;email:string;role:Role;is_active:boolean;created_at:string};
export async function getTeamUsers(signal:AbortSignal):Promise<TeamUser[]>{return requireOk(await apiFetch('/api/users',{signal}),'Team accounts could not be loaded.').then(response=>response.json());}
export async function createTeamUser(user:{name:string;email:string;password:string;role:Role}):Promise<TeamUser>{return requireOk(await apiFetch('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(user)}),'The staff account could not be created.').then(response=>response.json());}
export async function setTeamUserStatus(id:number,is_active:boolean):Promise<TeamUser>{return requireOk(await apiFetch(`/api/users/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({is_active})}),'The account status could not be updated.').then(response=>response.json());}

export type InboxMessage={id:number;external_message_id:string;sender_phone:string;message_text:string;analysis:{items:{requested_description:string;quantity:number|null;suggested_product:{name:string}|null;match_status:string}[];notes:string[]};received_at:string};
export async function getInboxMessages(signal:AbortSignal):Promise<InboxMessage[]>{return requireOk(await apiFetch('/api/integrations/whatsapp/messages',{signal}),'The message inbox could not be loaded.').then(response=>response.json());}

export type StockMovement={id:number;product_id:number;sku:string;product_name:string;order_id:number|null;quantity_delta:number;reason:string;created_at:string};
export async function getStockMovements(signal:AbortSignal):Promise<StockMovement[]>{return requireOk(await apiFetch('/api/stock-movements',{signal}),'Stock movement history could not be loaded.').then(response=>response.json());}

export type RestockDecision={id:number;product_id:number;decision:'accepted'|'dismissed';suggested_quantity:number;decision_date:string;decided_at:string};
export async function getRestockDecisions(signal:AbortSignal):Promise<RestockDecision[]>{return requireOk(await apiFetch('/api/operations/restock-decisions',{signal}),'Restock decisions could not be loaded.').then(response=>response.json());}
export async function saveRestockDecision(productId:number,decision:'accepted'|'dismissed',suggestedQuantity:number):Promise<RestockDecision>{return requireOk(await apiFetch(`/api/operations/restock-decisions/${productId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,suggested_quantity:suggestedQuantity})}),'The restock decision could not be saved.').then(response=>response.json());}

export type ProductImportRow={row:number;sku:string;name:string;category:string;price:string;stock:number;barcode?:string|null;imei?:string|null;phone_unit_action?:string|null;action:'create'|'update'};
export type ProductImportPreview={valid_rows:number;errors:string[];rows:ProductImportRow[]};
export async function previewProductImport(file:File):Promise<ProductImportPreview>{const form=new FormData();form.append('file',file);return requireOk(await apiFetch('/api/imports/products/preview',{method:'POST',body:form}),'The CSV preview could not be created.').then(response=>response.json());}
export async function applyProductImport(file:File):Promise<ProductImportPreview>{const form=new FormData();form.append('file',file);return requireOk(await apiFetch('/api/imports/products/apply?confirm=true',{method:'POST',body:form}),'The CSV could not be imported.').then(response=>response.json());}

export type SalesMetric={product_id:number;sku:string;name:string;quantity_sold:number;revenue:string};
export type SalesAnalytics={period_days:number;best_sellers:SalesMetric[];slow_movers:SalesMetric[];no_sale_products:SalesMetric[];category_revenue:Record<string,string>};
export type OperationalAlert={severity:'critical'|'warning'|'info';title:string;detail:string;href:string};
export async function getSalesAnalytics(signal:AbortSignal,days=7):Promise<SalesAnalytics>{return requireOk(await apiFetch(`/api/operations/analytics?days=${days}`,{signal}),'Sales analytics could not be loaded.').then(response=>response.json());}
export async function getOperationalAlerts(signal:AbortSignal):Promise<OperationalAlert[]>{return requireOk(await apiFetch('/api/operations/alerts',{signal}),'Operational alerts could not be loaded.').then(response=>response.json());}

export type ImportRecord={id:number;filename:string;imported_by:string;created_rows:number;updated_rows:number;imported_at:string};
export async function getImportHistory(signal:AbortSignal):Promise<ImportRecord[]>{return requireOk(await apiFetch('/api/imports/products/history',{signal}),'Import history could not be loaded.').then(response=>response.json());}
export type Supplier={id:number;name:string;contact_name:string;phone:string;email:string;supplied_skus:string;lead_time_days:number};
export async function getSuppliers(signal:AbortSignal):Promise<Supplier[]>{return requireOk(await apiFetch('/api/suppliers',{signal}),'Suppliers could not be loaded.').then(response=>response.json());}

export async function createSupplier(supplier:Omit<Supplier,'id'>):Promise<Supplier>{return requireOk(await apiFetch('/api/suppliers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(supplier)}),'Supplier could not be saved.').then(response=>response.json());}
