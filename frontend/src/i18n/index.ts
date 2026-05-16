import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./locales/en.json";
import sr from "./locales/sr.json";
import srCyrl from "./locales/sr-Cyrl.json";
import srLatn from "./locales/sr-Latn.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      "sr-Latn": { translation: srLatn },
      "sr-Cyrl": { translation: srCyrl },
      sr: { translation: sr },
      en: { translation: en },
    },
    fallbackLng: "sr-Latn",
    supportedLngs: ["sr-Latn", "sr-Cyrl", "sr", "en"],
    nonExplicitSupportedLngs: false,
    load: "currentOnly",
    detection: {
      order: ["localStorage", "sessionStorage", "cookie", "htmlTag", "navigator"],
      caches: ["localStorage"],
    },
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
