import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = '/api';
const STATUS_LABEL = { IN_STOCK: 'In stock', LOW_STOCK: 'Low stock', OUT_OF_STOCK: 'Out of stock' };
const money = (n) => n.toLocaleString(undefined, { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

async function call(path, options = {}) {
  const res = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) throw Error((await res.json().catch(() => ({}))).detail || 'Backend unavailable');
  return res.status === 204 ? null : res.json();
}

function App() {
  const [products, setProducts] = useState([]);
  const [stats, setStats] = useState({ products: 0, units: 0, lowStock: 0, outOfStock: 0, inventoryValue: 0 });
  const [filter, setFilter] = useState('ALL');
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setError('');
      const [list, s] = await Promise.all([call('/products'), call('/products/stats')]);
      setProducts(list);
      setStats(s);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const act = (fn) => async (...args) => {
    try { await fn(...args); await load(); } catch (e) { setError(e.message); }
  };
  const adjust = act((p, delta) => call(`/products/${p.id}/adjust`, { method: 'POST', body: JSON.stringify({ delta }) }));
  const remove = act((p) => confirm(`Delete ${p.name}?`) && call(`/products/${p.id}`, { method: 'DELETE' }));
  const create = act(async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = Object.fromEntries(new FormData(form));
    await call('/products', {
      method: 'POST',
      body: JSON.stringify({ ...f, quantity: +f.quantity, reorder_level: +f.reorder_level, unit_price: +f.unit_price }),
    });
    form.reset();
    setShowForm(false);
  });

  const visible = filter === 'ALL' ? products : products.filter((p) => p.stock_status === filter);
  const alerts = products.filter((p) => p.stock_status !== 'IN_STOCK').sort((a, b) => a.quantity - b.quantity);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div><b>StockPilot</b><small>Inventory Management</small></div>
        </div>
        <nav>
          <a className="active">▦ <span>Inventory</span></a>
          <a>⇅ <span>Stock moves</span></a>
          <a>◫ <span>Suppliers</span></a>
          <a>◌ <span>Reports</span></a>
        </nav>
        <div className="side-bottom">
          <div className="upgrade"><strong>Never run out.</strong><p>Reorder alerts fire when stock hits its reorder level.</p></div>
          <div className="profile"><div className="avatar">WM</div><div><b>Warehouse Manager</b><small>Main warehouse</small></div><span>⋮</span></div>
        </div>
      </aside>

      <main className="main">
        <header>
          <div>
            <p className="eyebrow">WAREHOUSE / OVERVIEW</p>
            <h1>Inventory overview</h1>
            <p className="muted">Stock levels, reorder alerts and inventory value at a glance.</p>
          </div>
          <button className="primary" onClick={() => setShowForm(true)}>＋ New product</button>
        </header>

        {error && <div className="alert">⚠ {error}</div>}

        <section className="stats">
          <Stat label="Products" value={stats.products} icon="▦" />
          <Stat label="Units in stock" value={stats.units} icon="⇅" />
          <Stat label="Low / out of stock" value={`${stats.lowStock} / ${stats.outOfStock}`} icon="⚠" />
          <Stat label="Inventory value" value={money(stats.inventoryValue)} icon="₹" />
        </section>

        <section className="content-grid">
          <div className="panel tasks-panel">
            <div className="panel-head">
              <div><h2>Products</h2><p className="muted">Receive (+) or ship (−) stock straight from the table.</p></div>
              <div className="filters">
                {['ALL', 'IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK'].map((x) => (
                  <button className={filter === x ? 'selected' : ''} onClick={() => setFilter(x)} key={x}>
                    {x === 'ALL' ? 'All' : STATUS_LABEL[x]}
                  </button>
                ))}
              </div>
            </div>
            {loading ? <div className="empty">Loading inventory…</div> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Product</th><th>Category</th><th>Stock</th><th>Unit price</th><th>Status</th><th></th></tr></thead>
                  <tbody>
                    {visible.map((p) => (
                      <tr key={p.id}>
                        <td><div className="task-title"><span className={`dot ${p.stock_status.toLowerCase()}`}></span>
                          <div><b>{p.name}</b><small>{p.sku}{p.supplier && ` · ${p.supplier}`}</small></div></div></td>
                        <td>{p.category}</td>
                        <td>
                          <div className="qty">
                            <button className="icon-btn" onClick={() => adjust(p, -1)} disabled={!p.quantity} title="Ship 1">−</button>
                            <b>{p.quantity}</b>
                            <button className="icon-btn" onClick={() => adjust(p, 1)} title="Receive 1">＋</button>
                          </div>
                          <small className="muted">reorder at {p.reorder_level}</small>
                        </td>
                        <td>{money(p.unit_price)}</td>
                        <td><span className={`status ${p.stock_status.toLowerCase()}`}>{STATUS_LABEL[p.stock_status]}</span></td>
                        <td><button className="icon-btn" onClick={() => remove(p)} title="Delete product">🗑</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!visible.length && <div className="empty">No products in this filter.</div>}
              </div>
            )}
          </div>

          <aside className="panel activity">
            <div className="panel-head"><div><h2>Reorder alerts</h2><p className="muted">Products at or below their reorder level.</p></div></div>
            {alerts.length ? alerts.slice(0, 6).map((p) => (
              <div className="activity-row" key={p.id}>
                <span className="activity-icon">{p.quantity ? '◔' : '✕'}</span>
                <div><b>{p.name}</b><small>{p.quantity} left · reorder at {p.reorder_level}</small></div>
              </div>
            )) : <div className="empty">All products are well stocked.</div>}
            <div className="pipeline"><span>CI</span><i></i><span>Build</span><i></i><span>Scan</span><i></i><span>Deploy</span></div>
          </aside>
        </section>

        {showForm && (
          <div className="modal-backdrop">
            <form className="modal" onSubmit={create}>
              <div className="modal-head">
                <div><p className="eyebrow">ADD PRODUCT</p><h2>Add a new product</h2></div>
                <button type="button" className="close" onClick={() => setShowForm(false)}>×</button>
              </div>
              <div className="form-row">
                <label>SKU<input name="sku" required maxLength={40} placeholder="e.g. KB-001" /></label>
                <label>Category<input name="category" defaultValue="General" /></label>
              </div>
              <label>Product name<input name="name" required placeholder="e.g. Mechanical keyboard" /></label>
              <label>Supplier<input name="supplier" placeholder="e.g. Acme Supplies" /></label>
              <div className="form-row">
                <label>Quantity<input name="quantity" type="number" min="0" defaultValue="0" required /></label>
                <label>Reorder level<input name="reorder_level" type="number" min="0" defaultValue="10" required /></label>
                <label>Unit price (₹)<input name="unit_price" type="number" min="0" step="0.01" defaultValue="0" required /></label>
              </div>
              <button className="primary full">Add product</button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, icon }) {
  return <div className="stat"><div className="stat-icon">{icon}</div><div><small>{label}</small><strong>{value}</strong><span>Updated just now</span></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
