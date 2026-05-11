const planters = [
  { name: "Basil line 03", zone: "Greenhouse A", moisture: 82, status: "Healthy", tone: "ok", last: "2 min ago" },
  { name: "Mint shelf 11", zone: "Retail room", moisture: 44, status: "Watch", tone: "warning", last: "9 min ago" },
  { name: "Lavender bed 2", zone: "Outdoor north", moisture: 18, status: "Dry", tone: "danger", last: "18 min ago" },
] as const;

export function UIKit() {
  return (
    <div className="po-app react-root">
      <aside className="po-sidebar">
        <a className="po-brand" href="/">
          <span className="po-brand-mark">P</span>
          <span>PlantOps</span>
        </a>
        <nav className="po-nav" aria-label="Primary">
          <a className="po-nav-link is-active" href="#overview">Overview</a>
          <a className="po-nav-link" href="#actions">Actions</a>
          <a className="po-nav-link" href="#forms">Forms</a>
          <a className="po-nav-link" href="#tables">Tables</a>
        </nav>
        <button className="po-btn po-btn-secondary po-mobile-menu" type="button">Menu</button>
      </aside>

      <section className="po-page">
        <header className="po-topbar" id="overview">
          <div className="po-title-block">
            <span className="po-eyebrow">React UI Kit</span>
            <h1 className="po-title">PlantOps components</h1>
            <p className="po-subtitle">
              React screens use the same production classes as Django templates and HTMX fragments.
            </p>
          </div>
          <div className="po-actions">
            <button className="po-btn po-btn-secondary" type="button">Preview</button>
            <button className="po-btn po-btn-primary" type="button">New task</button>
          </div>
        </header>

        <div className="po-grid po-grid-4">
          <Kpi label="Active planters" value="428" meta="+12 this week" />
          <Kpi label="Moisture average" value="71%" meta="Stable" />
          <Kpi label="Open alerts" value="9" meta="Needs review" tone="warning" />
          <Kpi label="Automation uptime" value="99.3%" meta="Healthy" />
        </div>

        <section className="po-section" id="actions">
          <div className="po-section-header">
            <div>
              <h2 className="po-section-title">Controls</h2>
              <p className="po-help">Buttons, segmented controls, badges, and state chips.</p>
            </div>
            <div className="po-segmented" aria-label="Time range">
              <button className="is-active" type="button">24h</button>
              <button type="button">7d</button>
              <button type="button">30d</button>
            </div>
          </div>
          <div className="po-panel po-stack">
            <div className="po-inline">
              <button className="po-btn po-btn-primary" type="button">Save</button>
              <button className="po-btn po-btn-secondary" type="button">Preview</button>
              <button className="po-btn po-btn-ghost" type="button">Cancel</button>
              <button className="po-btn po-btn-danger" type="button">Disable</button>
              <button className="po-btn po-btn-secondary po-icon-btn" type="button" aria-label="Refresh">R</button>
            </div>
            <div className="po-inline">
              <span className="po-badge">Tenant ready</span>
              <span className="po-status po-status-ok">Online</span>
              <span className="po-status po-status-warning">Delayed</span>
              <span className="po-status po-status-danger">Offline</span>
            </div>
          </div>
        </section>

        <section className="po-section" id="forms">
          <div className="po-section-header">
            <h2 className="po-section-title">Forms</h2>
            <span className="po-badge">React-ready</span>
          </div>
          <form className="po-panel po-form">
            <div className="po-grid po-grid-2">
              <label className="po-field-group">
                <span className="po-label">Planter name</span>
                <input className="po-field" defaultValue="Greenhouse row A" />
              </label>
              <label className="po-field-group">
                <span className="po-label">Irrigation profile</span>
                <select className="po-select" defaultValue="Balanced">
                  <option>Balanced</option>
                  <option>Dry climate</option>
                  <option>Propagation</option>
                </select>
              </label>
            </div>
            <label className="po-field-group">
              <span className="po-label">Operator note</span>
              <textarea className="po-textarea" defaultValue="Check sensors after the evening irrigation run." />
            </label>
            <label className="po-check-row">
              <input type="checkbox" defaultChecked />
              <span>Notify team when thresholds are exceeded</span>
            </label>
            <div className="po-actions">
              <button className="po-btn po-btn-secondary" type="reset">Reset</button>
              <button className="po-btn po-btn-primary" type="submit">Save profile</button>
            </div>
          </form>
        </section>

        <section className="po-section" id="tables">
          <div className="po-section-header">
            <div>
              <h2 className="po-section-title">Operational table</h2>
              <p className="po-help">Reusable table treatment for device and tenant workflows.</p>
            </div>
            <input className="po-field po-search" type="search" placeholder="Search planters" />
          </div>
          <div className="po-table-wrap">
            <table className="po-table">
              <thead>
                <tr>
                  <th>Planter</th>
                  <th>Zone</th>
                  <th>Moisture</th>
                  <th>Status</th>
                  <th>Last reading</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {planters.map((planter) => (
                  <tr key={planter.name}>
                    <td><strong>{planter.name}</strong></td>
                    <td>{planter.zone}</td>
                    <td>
                      <div className="po-meter" aria-label={`${planter.moisture} percent`}>
                        <span style={{ width: `${planter.moisture}%` }} />
                      </div>
                    </td>
                    <td><span className={`po-status po-status-${planter.tone}`}>{planter.status}</span></td>
                    <td>{planter.last}</td>
                    <td><button className="po-btn po-btn-secondary" type="button">Open</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </div>
  );
}

type KpiProps = {
  label: string;
  value: string;
  meta: string;
  tone?: "ok" | "warning" | "danger";
};

function Kpi({ label, value, meta, tone = "ok" }: KpiProps) {
  const metaClass = tone === "ok" ? "po-kpi-trend" : `po-status po-status-${tone}`;

  return (
    <article className="po-card po-kpi">
      <span className="po-kpi-label">{label}</span>
      <strong className="po-kpi-value">{value}</strong>
      <span className={metaClass}>{meta}</span>
    </article>
  );
}
