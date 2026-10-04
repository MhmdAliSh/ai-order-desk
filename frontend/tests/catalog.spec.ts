import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const catalog = JSON.parse(fs.readFileSync(new URL('../../sample-data/products.json',import.meta.url),'utf8')).map((p:any,i:number)=>({...p,id:i+1}));
test.beforeEach(async({page})=>{
 await page.addInitScript(()=>{if(!location.search.includes('auth=off'))localStorage.setItem('orderdesk-session',JSON.stringify({token:'playwright-test-token',email:'staff@example.test',role:'staff'}));});
 await page.route('**/api/products?*',route=>route.fulfill({json:catalog}));
});
test('dashboard displays real catalog totals and category navigation',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'A clearer view of your shop.'})).toBeVisible();
 await expect(page.getByText('Catalog connected')).toBeVisible();
 await expect(page.locator('.stat').first()).toContainText('50');
 await expect(page.locator('.stat').nth(1)).toContainText(String(catalog.reduce((n:number,p:any)=>n+p.stock,0)).replace(/\B(?=(\d{3})+(?!\d))/g,','));
 await page.locator('.category-legend').getByRole('button',{name:/Chargers/}).click();
 await expect(page.getByText('Showing 1–10 of 12 products')).toBeVisible();
});
test('search, filter, sorting, pagination, details and empty state',async({page})=>{
 await page.goto('/#products');
 await expect(page.getByText('Showing 1–10 of 50 products')).toBeVisible();
 await page.getByRole('button',{name:'Next page',exact:true}).click();
 await expect(page.getByText('Showing 11–20 of 50 products')).toBeVisible();
 await page.getByRole('textbox',{name:'Search products'}).fill('DEMO-CHG-001');
 await expect(page.getByText('Showing 1–1 of 1 products')).toBeVisible();
 await page.locator('.product-name').click();
 await expect(page.getByRole('dialog')).toContainText('USB-C wall charger 20W - White');
 await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'Clear search'}).click();
 await page.getByLabel('Filter by stock').selectOption('Out of stock');
 await expect(page.getByText('Showing 1–4 of 4 products')).toBeVisible();
 await page.getByLabel('Filter by stock').selectOption('All stock');
 await page.getByLabel('Sort products').selectOption('price-up');
 await expect(page.locator('tbody tr').first()).toContainText('$2.50');
 await page.getByRole('textbox',{name:'Search products'}).fill('does-not-exist');
 await expect(page.getByRole('heading',{name:'No matching products'})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters'}).click();
 await expect(page.getByText('Showing 1–10 of 50 products')).toBeVisible();
});
test('backend error can be retried',async({page})=>{
 await page.route('**/api/products?*',route=>route.fulfill({status:503,body:'Unavailable'}));
 await page.goto('/');
 await expect(page.getByRole('alert')).toContainText('We could not reach your catalog');
 await page.route('**/api/products?*',route=>route.fulfill({json:catalog}));
 await page.getByRole('button',{name:'Try again'}).click();
 await expect(page.getByText('Catalog connected')).toBeVisible();
 await expect(page.getByRole('alert')).not.toBeVisible();
});
test('empty catalog is explained',async({page})=>{
 await page.route('**/api/products?*',route=>route.fulfill({json:[]}));
 await page.goto('/#products');
 await expect(page.getByRole('heading',{name:'Your catalog is empty'})).toBeVisible();
});
test('catalog fetch includes subsequent API pages',async({page})=>{
 const hundred=Array.from({length:100},(_,i)=>({...catalog[i%50],id:i+1,sku:'TEST-'+i}));
 await page.route('**/api/products?*',route=>route.fulfill({json:route.request().url().includes('offset=0')?hundred:[{...catalog[0],id:101,sku:'LAST'}]}));
 await page.goto('/#products');
 await expect(page.getByText('Showing 1–10 of 101 products')).toBeVisible();
 await page.getByRole('textbox',{name:'Search products'}).fill('LAST');
 await expect(page.getByText('Showing 1–1 of 1 products')).toBeVisible();
});
test('mobile navigation and layout',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'A clearer view of your shop.'})).toBeVisible();
 await page.getByRole('button',{name:'Open navigation'}).click();
 await page.getByRole('link',{name:/Products/}).click();
 await expect(page.getByRole('heading',{name:'Your product catalog.'})).toBeVisible();
 const layout = await page.evaluate(() => {
  const tableScroll = document.querySelector<HTMLElement>('.table-scroll')!;
  return {
   pageOverflow: getComputedStyle(document.documentElement).overflowX,
   tableScrollsInsideCard: tableScroll.scrollWidth > tableScroll.clientWidth,
  };
 });
 expect(layout).toEqual({pageOverflow:'clip',tableScrollsInsideCard:true});
});

test('manual order draft uses a selected customer and catalog prices', async ({ page }) => {
 const customer = {id: 1, name: 'Cedar Mobile', contact_name: 'Rami Haddad', phone: '+961 3 456 201', email: 'rami@cedarmobile.example'};
 await page.route('**/api/customers', route => route.fulfill({json: [customer]}));
 await page.route('**/api/orders', async route => {
  if (route.request().method() === 'GET') return route.fulfill({json: []});
  expect(route.request().postDataJSON()).toEqual({customer_id: 1, items: [{product_id: 1, quantity: 2}]});
  return route.fulfill({json: {id: 7, customer, status: 'draft', total: '19.00', created_at: '2026-09-25T12:00:00', items: []}});
 });
 await page.goto('/#new-order');
 await page.getByLabel('Customer').selectOption('1');
 await page.getByLabel('Add product').fill('DEMO-CHG-001');
 await page.getByRole('button', {name: /USB-C wall charger 20W - White/}).click();
 await page.getByRole('button', {name: 'Increase USB-C wall charger 20W - White'}).click();
 await expect(page.getByText('$19.00').last()).toBeVisible();
 await page.getByRole('button', {name: 'Save draft'}).click();
 await expect(page.getByRole('status')).toContainText('Draft #7 saved for Cedar Mobile');
});

test('AI intake can dismiss unwanted items before saving a reviewed draft', async ({page}) => {
 const customer = {id: 1, name: 'Cedar Mobile', contact_name: 'Rami Haddad', phone: '+961 3 456 201', email: 'rami@cedarmobile.example'};
 await page.route('**/api/customers', route => route.fulfill({json: [customer]}));
 await page.route('**/api/order-intake/analyze', route => route.fulfill({json: {mode:'demo',notes:[],items:[
  {requested_description:'mystery widgets',quantity:2,suggested_product:null,match_status:'needs_review',evidence:'No reliable match.'},
  {requested_description:'20W charger',quantity:1,suggested_product:{id:1,sku:catalog[0].sku,name:catalog[0].name,stock:catalog[0].stock},match_status:'matched',evidence:'Matched.'},
 ]}}));
 await page.route('**/api/orders', async route => {
  expect(route.request().postDataJSON()).toEqual({customer_id:1,items:[{product_id:1,quantity:1}]});
  return route.fulfill({json:{id:8,customer,status:'draft',total:'9.50',created_at:'2026-09-28T12:00:00',items:[]}});
 });
 await page.goto('/#ai-intake');
 await page.getByLabel('AI customer').selectOption('1');
 await page.getByLabel('Customer message').fill('Please send two mystery widgets and one 20W charger.');
 await page.getByRole('button',{name:'Analyze message'}).click();
 await expect(page.getByText('2 items')).toBeVisible();
 await page.getByRole('button',{name:'Dismiss mystery widgets'}).click();
 await expect(page.getByText('mystery widgets',{exact:true})).not.toBeVisible();
 await page.getByRole('button',{name:'Save reviewed draft'}).click();
 await expect(page.getByRole('status')).toContainText('Draft #8 saved for Cedar Mobile');
});

test('entry screen separates the customer portal from team sign-in', async ({page}) => {
 await page.goto('/?auth=off');
 await expect(page.getByRole('heading',{name:'Where would you like to go?'})).toBeVisible();
 await page.getByRole('button',{name:/Customer portal/}).click();
 await expect(page.getByRole('heading',{name:'Your own space is on the way.'})).toBeVisible();
 await expect(page.getByText('CUSTOMER ACCESS IS NOT OPEN YET')).toBeVisible();
 await page.getByRole('button',{name:/All workspaces/}).click();
 await page.getByRole('button',{name:/Team workspace/}).click();
 await page.route('**/api/auth/login',route=>route.fulfill({json:{token:'team-session-token',email:'staff@example.test',role:'staff'}}));
 await page.getByLabel('Email address').fill('staff@example.test');
 await page.getByLabel('Password').fill('staff-password');
 await page.getByRole('button',{name:/Sign in to team workspace/}).click();
 await expect(page.getByRole('heading',{name:'A clearer view of your shop.'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Admin'})).toHaveCount(0);
});
