import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button, Badge, StatusBadge, KpiCard, Alert, Meter } from "@/components/ui";

type SupportedLanguage = "sr-Latn" | "sr-Cyrl" | "en";

const languageOptions: Array<{ code: SupportedLanguage; labelKey: string }> = [
  { code: "sr-Latn", labelKey: "language.srLatn" },
  { code: "sr-Cyrl", labelKey: "language.srCyrl" },
  { code: "en", labelKey: "language.en" },
];

const planters = [
  { id: "basil",    moisture: 82, tone: "ok"      as const, zone: "Greenhouse A" },
  { id: "mint",     moisture: 44, tone: "warning"  as const, zone: "Retail room"  },
  { id: "lavender", moisture: 18, tone: "danger"   as const, zone: "Outdoor north" },
];

function resolveSupportedLanguage(language = ""): SupportedLanguage {
  const normalized = language.toLowerCase();
  if (normalized.startsWith("sr-cyrl")) return "sr-Cyrl";
  if (normalized.startsWith("en")) return "en";
  return "sr-Latn";
}

export function UIKit() {
  const { t, i18n } = useTranslation();
  const currentLanguage = resolveSupportedLanguage(i18n.resolvedLanguage ?? i18n.language);

  useEffect(() => {
    document.documentElement.lang = currentLanguage;
  }, [currentLanguage]);

  const changeLanguage = (language: SupportedLanguage) => {
    void i18n.changeLanguage(language);
  };

  return (
    <div className="fw-app react-root">

      {/* Sidebar */}
      <aside className="fw-sidebar">
        <a className="fw-brand" href="/">
          <span className="fw-brand-mark">F</span>
          <span>Flower</span>
        </a>
        <nav className="fw-nav" aria-label={t("nav.primary")}>
          <a className="fw-nav-link is-active" href="#overview">{t("nav.overview")}</a>
          <a className="fw-nav-link" href="#tokens">{t("nav.tokens")}</a>
          <a className="fw-nav-link" href="#actions">{t("nav.actions")}</a>
          <a className="fw-nav-link" href="#forms">{t("nav.forms")}</a>
          <a className="fw-nav-link" href="#tables">{t("nav.tables")}</a>
        </nav>

        <div className="fw-sidebar-footer">
          <div className="fw-segmented" aria-label={t("language.aria")}>
            {languageOptions.map((lang) => (
              <button
                key={lang.code}
                type="button"
                aria-pressed={currentLanguage === lang.code}
                className={currentLanguage === lang.code ? "is-active" : undefined}
                onClick={() => changeLanguage(lang.code)}
              >
                {t(lang.labelKey)}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Page */}
      <section className="fw-page">
        <div className="fw-page-body">

          {/* Hero */}
          <div className="fw-page-header" id="overview">
            <div className="fw-title-block">
              <span className="fw-eyebrow">{t("hero.eyebrow")}</span>
              <h1 className="fw-title">Flower UI Kit</h1>
              <p className="fw-subtitle">{t("hero.subtitle")}</p>
            </div>
            <div className="fw-actions">
              <Button variant="secondary">{t("hero.preview")}</Button>
              <Button variant="primary">{t("hero.newTask")}</Button>
            </div>
          </div>

          {/* KPI row */}
          <div className="fw-grid fw-grid-4">
            <KpiCard label={t("kpi.activePlanters")} value="428" meta={t("kpi.activePlantersMeta")} />
            <KpiCard label={t("kpi.moistureAverage")} value="71%" meta={t("kpi.stable")} />
            <KpiCard label={t("kpi.openAlerts")} value="9" meta={t("kpi.needsReview")} tone="warning" metaIsStatus />
            <KpiCard label={t("kpi.automationUptime")} value="99.3%" meta={t("kpi.healthy")} tone="ok" metaIsStatus />
          </div>

          {/* Tokens */}
          <section className="fw-section" id="tokens">
            <div className="fw-section-header">
              <div>
                <h2 className="fw-section-title">{t("tokens.title")}</h2>
                <p className="fw-help">{t("tokens.help")}</p>
              </div>
            </div>
            <div className="fw-grid fw-grid-4">
              <div className="fw-card fw-kpi">
                <span className="fw-label">{t("tokens.surface")}</span>
                <strong className="fw-kpi-value">#F7F4ED</strong>
              </div>
              <div className="fw-card fw-kpi">
                <span className="fw-label">{t("tokens.primary")}</span>
                <strong className="fw-kpi-value">#256D4F</strong>
              </div>
              <div className="fw-card fw-kpi">
                <span className="fw-label">{t("tokens.warning")}</span>
                <strong className="fw-kpi-value">#B7791F</strong>
              </div>
              <div className="fw-card fw-kpi">
                <span className="fw-label">{t("tokens.danger")}</span>
                <strong className="fw-kpi-value">#B42318</strong>
              </div>
            </div>
          </section>

          {/* Buttons, badges, statuses */}
          <section className="fw-section" id="actions">
            <div className="fw-section-header">
              <div>
                <h2 className="fw-section-title">{t("controls.title")}</h2>
                <p className="fw-help">{t("controls.help")}</p>
              </div>
              <div className="fw-segmented" aria-label={t("controls.timeRange")}>
                <button className="is-active" type="button">24h</button>
                <button type="button">7d</button>
                <button type="button">30d</button>
              </div>
            </div>
            <div className="fw-panel fw-stack">
              <div className="fw-inline">
                <Button variant="primary">{t("controls.save")}</Button>
                <Button variant="secondary">{t("controls.preview")}</Button>
                <Button variant="ghost">{t("controls.cancel")}</Button>
                <Button variant="danger">{t("controls.disable")}</Button>
                <Button variant="secondary" iconOnly aria-label={t("controls.refresh")}>↺</Button>
              </div>
              <div className="fw-inline">
                <Badge>{t("controls.tenantReady")}</Badge>
                <Badge variant="neutral">{t("controls.draft")}</Badge>
                <Badge variant="accent">{t("controls.provider")}</Badge>
                <StatusBadge tone="ok">{t("controls.online")}</StatusBadge>
                <StatusBadge tone="warning">{t("controls.delayed")}</StatusBadge>
                <StatusBadge tone="danger">{t("controls.offline")}</StatusBadge>
                <StatusBadge tone="info">{t("controls.pending")}</StatusBadge>
              </div>
            </div>
          </section>

          {/* Alerts */}
          <section className="fw-section" id="alerts">
            <div className="fw-section-header">
              <h2 className="fw-section-title">{t("alerts.title")}</h2>
            </div>
            <div className="fw-stack">
              <Alert title={t("alerts.info")}>{t("alerts.infoBody")}</Alert>
              <Alert variant="success" title={t("alerts.success")}>{t("alerts.successBody")}</Alert>
              <Alert variant="warning" title={t("alerts.warning")}>{t("alerts.warningBody")}</Alert>
              <Alert variant="danger" title={t("alerts.danger")}>{t("alerts.dangerBody")}</Alert>
            </div>
          </section>

          {/* Forms */}
          <section className="fw-section" id="forms">
            <div className="fw-section-header">
              <h2 className="fw-section-title">{t("forms.title")}</h2>
              <Badge>{t("forms.reactReady")}</Badge>
            </div>
            <form className="fw-panel fw-form" key={currentLanguage} onSubmit={(e) => e.preventDefault()}>
              <div className="fw-grid fw-grid-2">
                <label className="fw-field-group">
                  <span className="fw-label">{t("forms.planterName")}</span>
                  <input className="fw-field" defaultValue={t("forms.planterNameValue")} />
                </label>
                <label className="fw-field-group">
                  <span className="fw-label">{t("forms.irrigationProfile")}</span>
                  <select className="fw-select" defaultValue={t("forms.balanced")}>
                    <option>{t("forms.balanced")}</option>
                    <option>{t("forms.dryClimate")}</option>
                    <option>{t("forms.propagation")}</option>
                  </select>
                </label>
              </div>
              <label className="fw-field-group">
                <span className="fw-label">{t("forms.operatorNote")}</span>
                <textarea className="fw-textarea" defaultValue={t("forms.operatorNoteValue")} />
                <span className="fw-help">{t("forms.noteHelp")}</span>
              </label>
              <label className="fw-check-row">
                <input type="checkbox" defaultChecked />
                <span>{t("forms.notifyTeam")}</span>
              </label>
              <div className="fw-actions">
                <Button variant="ghost" type="reset">{t("forms.reset")}</Button>
                <Button variant="primary" type="submit">{t("forms.saveProfile")}</Button>
              </div>
            </form>
          </section>

          {/* Table */}
          <section className="fw-section" id="tables">
            <div className="fw-section-header">
              <div>
                <h2 className="fw-section-title">{t("table.title")}</h2>
                <p className="fw-help">{t("table.help")}</p>
              </div>
              <input className="fw-field fw-search" type="search" placeholder={t("table.search")} />
            </div>
            <div className="fw-table-wrap">
              <table className="fw-table">
                <thead>
                  <tr>
                    <th>{t("table.planter")}</th>
                    <th>{t("table.zone")}</th>
                    <th>{t("table.moisture")}</th>
                    <th>{t("table.status")}</th>
                    <th>{t("table.lastReading")}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {planters.map((planter) => (
                    <tr key={planter.id}>
                      <td><strong>{t(`planters.${planter.id}.name`)}</strong></td>
                      <td>{planter.zone}</td>
                      <td>
                        <Meter value={planter.moisture} tone={planter.tone} />
                      </td>
                      <td>
                        <StatusBadge tone={planter.tone}>
                          {t(`planters.${planter.id}.status`)}
                        </StatusBadge>
                      </td>
                      <td className="fw-dimmed">{t(`planters.${planter.id}.last`)}</td>
                      <td>
                        <Button variant="secondary" size="sm">{t("table.open")}</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Empty & skeleton */}
          <section className="fw-section" id="states">
            <div className="fw-section-header">
              <h2 className="fw-section-title">{t("states.title")}</h2>
            </div>
            <div className="fw-grid fw-grid-2">
              <div className="fw-empty">
                <div className="fw-empty-icon">🌿</div>
                <p className="fw-empty-title">{t("states.emptyTitle")}</p>
                <p className="fw-dimmed">{t("states.emptyBody")}</p>
              </div>
              <div className="fw-card">
                <div className="fw-skeleton fw-skeleton-text" style={{ width: "40%", height: "0.75rem" }} />
                <div className="fw-skeleton fw-skeleton-text" style={{ width: "70%", height: "2rem", margin: "0.5rem 0" }} />
                <div className="fw-skeleton fw-skeleton-block" style={{ height: "8px", marginTop: "0.75rem" }} />
              </div>
            </div>
          </section>

        </div>
      </section>

    </div>
  );
}
