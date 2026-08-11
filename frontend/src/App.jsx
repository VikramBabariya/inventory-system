import { useState, useEffect, useCallback } from 'react'
import './App.css'

const API_BASE = '/api'

function StatusBadge({ stock }) {
  if (stock <= 0) return <span className="badge badge-danger">Out of Stock</span>
  if (stock <= 10) return <span className="badge badge-warning">Low Stock</span>
  return <span className="badge badge-success">In Stock</span>
}

function ProductRow({ product, onMovement }) {
  return (
    <tr>
      <td className="sku">{product.sku}</td>
      <td>{product.name}</td>
      <td>{product.category?.name ?? '—'}</td>
      <td className="price">${parseFloat(product.price).toFixed(2)}</td>
      <td className="stock-num">{product.current_stock}</td>
      <td><StatusBadge stock={product.current_stock} /></td>
      <td className="actions">
        <button
          className="btn btn-sm btn-restock"
          onClick={() => onMovement(product, 'RESTOCK')}
        >+ Restock</button>
        <button
          className="btn btn-sm btn-sale"
          onClick={() => onMovement(product, 'SALE')}
          disabled={product.current_stock <= 0}
        >− Sale</button>
      </td>
    </tr>
  )
}

function MovementModal({ product, type, onClose, onConfirm }) {
  const [amount, setAmount] = useState(1)
  const [error, setError] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const qty = parseInt(amount, 10)
    if (!qty || qty <= 0) {
      setError('Enter a positive number.')
      return
    }
    if (type === 'SALE' && qty > product.current_stock) {
      setError(`Only ${product.current_stock} units available.`)
      return
    }
    onConfirm(product.id, type, qty)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>{type === 'RESTOCK' ? '📦 Restock' : '🛒 Record Sale'}</h2>
        <p className="modal-product">{product.name} <span className="sku">({product.sku})</span></p>
        <p className="modal-stock">Current stock: <strong>{product.current_stock}</strong></p>
        <form onSubmit={handleSubmit}>
          <label>
            Quantity
            <input
              type="number"
              min="1"
              value={amount}
              onChange={e => { setAmount(e.target.value); setError('') }}
              autoFocus
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className={`btn ${type === 'RESTOCK' ? 'btn-restock' : 'btn-sale'}`}>
              Confirm
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function App() {
  const [products, setProducts] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modal, setModal] = useState(null) // { product, type }
  const [toast, setToast] = useState(null)

  const showToast = useCallback((msg, ok = true) => {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/products`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setProducts(data)
      setError(null)
    } catch (err) {
      setError('Failed to load products. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      setHealth(data)
    } catch {
      setHealth({ status: 'unhealthy' })
    }
  }, [])

  useEffect(() => {
    fetchProducts()
    fetchHealth()
  }, [fetchProducts, fetchHealth])

  async function handleMovement(productId, type, amount) {
    const delta = type === 'SALE' ? -amount : amount
    try {
      const res = await fetch(`${API_BASE}/products/${productId}/movements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ change_amount: delta, movement_type: type }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail ?? `HTTP ${res.status}`)
      }
      showToast(`${type === 'RESTOCK' ? 'Restock' : 'Sale'} recorded successfully.`)
      setModal(null)
      fetchProducts()
    } catch (err) {
      showToast(err.message, false)
    }
  }

  const totalProducts = products.length
  const outOfStock = products.filter(p => p.current_stock <= 0).length
  const lowStock = products.filter(p => p.current_stock > 0 && p.current_stock <= 10).length
  const totalValue = products.reduce((sum, p) => sum + parseFloat(p.price) * p.current_stock, 0)

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <span className="header-icon">📦</span>
          <div>
            <h1>Inventory System</h1>
            <p className="header-sub">Warehouse Management Dashboard</p>
          </div>
        </div>
        <div className="header-right">
          {health && (
            <span className={`health-badge ${health.status === 'healthy' ? 'health-ok' : 'health-err'}`}>
              {health.status === 'healthy' ? '● Connected' : '● Disconnected'}
            </span>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => { setLoading(true); fetchProducts(); fetchHealth() }}>
            ↻ Refresh
          </button>
        </div>
      </header>

      <main className="main">
        {/* Stats */}
        <div className="stats">
          <div className="stat-card">
            <span className="stat-value">{totalProducts}</span>
            <span className="stat-label">Total Products</span>
          </div>
          <div className="stat-card stat-warning">
            <span className="stat-value">{lowStock}</span>
            <span className="stat-label">Low Stock</span>
          </div>
          <div className="stat-card stat-danger">
            <span className="stat-value">{outOfStock}</span>
            <span className="stat-label">Out of Stock</span>
          </div>
          <div className="stat-card stat-info">
            <span className="stat-value">${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
            <span className="stat-label">Stock Value</span>
          </div>
        </div>

        {/* Table */}
        <div className="table-card">
          <div className="table-header">
            <h2>Products</h2>
          </div>

          {loading && <div className="state-msg">Loading products…</div>}
          {error && <div className="state-msg state-error">{error}</div>}

          {!loading && !error && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Stock</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.length === 0 ? (
                    <tr><td colSpan="7" className="empty-row">No products found.</td></tr>
                  ) : (
                    products.map(p => (
                      <ProductRow
                        key={p.id}
                        product={p}
                        onMovement={(product, type) => setModal({ product, type })}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Movement Modal */}
      {modal && (
        <MovementModal
          product={modal.product}
          type={modal.type}
          onClose={() => setModal(null)}
          onConfirm={handleMovement}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.ok ? 'toast-ok' : 'toast-err'}`}>
          {toast.ok ? '✓' : '✗'} {toast.msg}
        </div>
      )}
    </div>
  )
}
