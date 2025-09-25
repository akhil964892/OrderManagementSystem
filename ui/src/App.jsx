import React, { useState } from 'react'

const INV = import.meta.env.VITE_INV || 'http://localhost:8001'
const ORD = import.meta.env.VITE_ORD || 'http://localhost:8002'
const SHP = import.meta.env.VITE_SHP || 'http://localhost:8003'

export default function App(){
  const [sku, setSku] = useState('ABC')
  const [pname, setPname] = useState('Widget')
  const [price, setPrice] = useState(100)
  const [qty, setQty] = useState(50)
  const [orderQty, setOrderQty] = useState(2)
  const [customer, setCustomer] = useState('Alice')
  const [orderId, setOrderId] = useState(null)
  const [logs, setLogs] = useState([])

  const log = (m) => setLogs(l => [m, ...l])

  async function addProduct(){
    const r = await fetch(`${INV}/products`, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({sku, name:pname, price: Number(price), qty: Number(qty)})})
    const t = await r.text()
    log(`Add product: ${r.status} ${t}`)
  }

  async function placeOrder(){
    const r = await fetch(`${ORD}/orders`, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({items:[{sku, qty:Number(orderQty)}], customer:{name:customer}})})
    const t = await r.json().catch(()=>({}))
    log(`Place order: ${r.status} ${JSON.stringify(t)}`)
    if (t.id) setOrderId(t.id)
  }

  async function getInvoice(){
    if (!orderId) return
    const r = await fetch(`${ORD}/orders/${orderId}/invoice`)
    const t = await r.json()
    log(`Invoice: ${JSON.stringify(t)}`)
  }

  async function getInvoicePdf(){
    if (!orderId) return
    const url = `${ORD}/orders/${orderId}/invoice.pdf`
    window.open(url, '_blank')
  }

  async function getShipping(){
    if (!orderId) return
    const r = await fetch(`${SHP}/shipping/${orderId}`)
    const t = await r.text()
    log(`Shipping: ${r.status} ${t}`)
  }

  return (
    <div style={{fontFamily:'system-ui', padding:20, maxWidth:900, margin:'0 auto'}}>
      <h2>Order Management Demo</h2>
      <p style={{opacity:.7}}>Inventory → Order (invoice & event) → Shipping (consumer)</p>

      <section style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:20}}>
        <div style={{border:'1px solid #ddd', padding:12, borderRadius:8}}>
          <h3>Add Product</h3>
          <label>SKU <input value={sku} onChange={e=>setSku(e.target.value)} /></label><br/>
          <label>Name <input value={pname} onChange={e=>setPname(e.target.value)} /></label><br/>
          <label>Price <input type="number" value={price} onChange={e=>setPrice(e.target.value)} /></label><br/>
          <label>Qty <input type="number" value={qty} onChange={e=>setQty(e.target.value)} /></label><br/>
          <button onClick={addProduct}>Add Product</button>
        </div>

        <div style={{border:'1px solid #ddd', padding:12, borderRadius:8}}>
          <h3>Place Order</h3>
          <label>SKU <input value={sku} onChange={e=>setSku(e.target.value)} /></label><br/>
          <label>Order Qty <input type="number" value={orderQty} onChange={e=>setOrderQty(e.target.value)} /></label><br/>
          <label>Customer <input value={customer} onChange={e=>setCustomer(e.target.value)} /></label><br/>
          <button onClick={placeOrder}>Place Order</button>
          <div style={{marginTop:8}}>Order ID: <b>{orderId ?? '-'}</b></div>
          <div style={{display:'flex', gap:8, marginTop:8}}>
            <button onClick={getInvoice}>Invoice JSON</button>
            <button onClick={getInvoicePdf}>Invoice PDF</button>
            <button onClick={getShipping}>Shipping Status</button>
          </div>
        </div>
      </section>

      <details open>
        <summary>Logs</summary>
        <pre style={{background:'#f7f7f7', padding:12, borderRadius:8, height:240, overflow:'auto'}}>
{logs.map((l,i)=>(<div key={i}>{l}</div>))}
        </pre>
      </details>

      <footer style={{marginTop:20, opacity:.7}}>
        <div>ENV: INV={INV} | ORD={ORD} | SHP={SHP}</div>
      </footer>
    </div>
  )
}
