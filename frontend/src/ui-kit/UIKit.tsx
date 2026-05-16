import { useEffect } from "react";
import { useTranslation } from "react-i18next";

type SupportedLanguage = "sr-Latn" | "sr-Cyrl" | "en";

const languageOptions: Array<{ code: SupportedLanguage; labelKey: string }> = [
  { code: "sr-Latn", labelKey: "language.srLatn" },
  { code: "sr-Cyrl", labelKey: "language.srCyrl" },
  { code: "en", labelKey: "language.en" },
];

const planters = [
  { id: "basil", moisture: 82, tone: "ok" },
  { id: "mint", moisture: 44, tone: "warning" },
  { id: "lavender", moisture: 18, tone: "danger" },
] as const;

function resolveSupportedLanguage(language = ""): SupportedLanguage {
  const normalized = language.toLowerCase();

  if (normalized.startsWith("sr-cyrl")) {
    return "sr-Cyrl";
  }

  if (normalized.startsWith("en")) {
    return "en";
  }

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
    <div className="po-app react-root">
      <aside className="po-sidebar">
        <a className="po-brand" href="/">
          <span className="po-brand-mark">P</span>
          <span>PlantOps</span>
        </a>
        <nav className="po-nav" aria-label={t("nav.primary")}>
          <a className="po-nav-link is-active" href="#overview">{t("nav.overview")}</a>
          <a className="po-nav-link" href="#actions">{t("nav.actions")}</a>
          <a className="po-nav-link" href="#forms">{t("nav.forms")}</a>
          <a className="po-nav-link" href="#tables">{t("nav.tables")}</a>
        </nav>
        <button className="po-btn po-btn-secondary po-mobile-menu" type="button">{t("nav.menu")}</button>
      </aside>

      <section className="po-page">
        <header className="po-topbar" id="overview">
          <div className="po-title-block">
            <span className="po-eyebrow">{t("hero.eyebrow")}</span>
            <h1 className="po-title">{t("hero.title")}</h1>
            <p className="po-subtitle">{t("hero.subtitle")}</p>
          </div>
          <div className="po-actions">
            <div className="po-segmented" aria-label={t("language.aria")}>
              {languageOptions.map((language) => (
                <button
                  aria-pressed={currentLanguage === language.code}
                  className={currentLanguage === language.code ? "is-active" : undefined}
                  key={language.code}
                  onClick={() => changeLanguage(language.code)}
                  type="button"
                >
                  {t(language.labelKey)}
                </button>
              ))}
            </div>
            <button className="po-btn po-btn-secondary" type="button">{t("hero.preview")}</button>
            <button className="po-btn po-btn-primary" type="button">{t("hero.newTask")}</button>
          </div>
        </header>

        <div className="po-grid po-grid-4">
          <Kpi label={t("kpi.activePlanters")} value="428" meta={t("kpi.activePlantersMeta")} />
          <Kpi label={t("kpi.moistureAverage")} value="71%" meta={t("kpi.stable")} />
          <Kpi label={t("kpi.openAlerts")} value="9" meta={t("kpi.needsReview")} tone="warning" />
          <Kpi label={t("kpi.automationUptime")} value="99.3%" meta={t("kpi.healthy")} />
        </div>

        <section className="po-section" id="actions">
          <div className="po-section-header">
            <div>
              <h2 className="po-section-title">{t("controls.title")}</h2>
              <p className="po-help">{t("controls.help")}</p>
            </div>
            <div className="po-segmented" aria-label={t("controls.timeRange")}>
              <button className="is-active" type="button">24h</button>
              <button type="button">7d</button>
              <button type="button">30d</button>
            </div>
          </div>
          <div className="po-panel po-stack">
            <div className="po-inline">
              <button className="po-btn po-btn-primary" type="button">{t("controls.save")}</button>
              <button className="po-btn po-btn-secondary" type="button">{t("controls.preview")}</button>
              <button className="po-btn po-btn-ghost" type="button">{t("controls.cancel")}</button>
              <button className="po-btn po-btn-danger" type="button">{t("controls.disable")}</button>
              <button className="po-btn po-btn-secondary po-icon-btn" type="button" aria-label={t("controls.refresh")}>R</button>
            </div>
            <div className="po-inline">
              <span className="po-badge">{t("controls.tenantReady")}</span>
              <span className="po-status po-status-ok">{t("controls.online")}</span>
              <span className="po-status po-status-warning">{t("controls.delayed")}</span>
              <span className="po-status po-status-danger">{t("controls.offline")}</span>
            </div>
          </div>
        </section>

        <section className="po-section" id="forms">
          <div className="po-section-header">
            <h2 className="po-section-title">{t("forms.title")}</h2>
            <span className="po-badge">{t("forms.reactReady")}</span>
          </div>
          <form className="po-panel po-form" key={currentLanguage}>
            <div className="po-grid po-grid-2">
              <label className="po-field-group">
                <span className="po-label">{t("forms.planterName")}</span>
                <input className="po-field" defaultValue={t("forms.planterNameValue")} />
              </label>
              <label className="po-field-group">
                <span className="po-label">{t("forms.irrigationProfile")}</span>
                <select className="po-select" defaultValue={t("forms.balanced")}>
                  <option>{t("forms.balanced")}</option>
                  <option>{t("forms.dryClimate")}</option>
                  <option>{t("forms.propagation")}</option>
                </select>
              </label>
            </div>
            <label className="po-field-group">
              <span className="po-label">{t("forms.operatorNote")}</span>
              <textarea className="po-textarea" defaultValue={t("forms.operatorNoteValue")} />
            </label>
            <label className="po-check-row">
              <input type="checkbox" defaultChecked />
              <span>{t("forms.notifyTeam")}</span>
            </label>
            <div className="po-actions">
              <button className="po-btn po-btn-secondary" type="reset">{t("forms.reset")}</button>
              <button className="po-btn po-btn-primary" type="submit">{t("forms.saveProfile")}</button>
            </div>
          </form>
        </section>

        <section className="po-section" id="tables">
          <div className="po-section-header">
            <div>
              <h2 className="po-section-title">{t("table.title")}</h2>
              <p className="po-help">{t("table.help")}</p>
            </div>
            <input className="po-field po-search" type="search" placeholder={t("table.search")} />
          </div>
          <div className="po-table-wrap">
            <table className="po-table">
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
                    <td>{t(`planters.${planter.id}.zone`)}</td>
                    <td>
                      <div className="po-meter" aria-label={t("table.meterAria", { value: planter.moisture })}>
                        <span style={{ width: `${planter.moisture}%` }} />
                      </div>
                    </td>
                    <td><span className={`po-status po-status-${planter.tone}`}>{t(`planters.${planter.id}.status`)}</span></td>
                    <td>{t(`planters.${planter.id}.last`)}</td>
                    <td><button className="po-btn po-btn-secondary" type="button">{t("table.open")}</button></td>
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
