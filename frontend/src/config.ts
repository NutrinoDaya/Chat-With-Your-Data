import rawConfig from '../config/config.json';

/// <reference types="vite/client" />

type Environment = 'development' | 'production';

interface ChartOptions {
  width: number;
  height: number;
  theme: 'light' | 'dark';
  colors: string[];
  animation: boolean;
}

interface TableOptions {
  pageSize: number;
  sortable: boolean;
  filterable: boolean;
  exportable: boolean;
}

interface UIConfig {
  theme: 'light' | 'dark';
  primaryColor: string;
  fontSize: string;
  fontFamily: string;
}

interface Features {
  enableCharts: boolean;
  enableRealtime: boolean;
  enableDataSources: string[];
}

export interface Config {
  apiBaseUrl: string;
  wsBaseUrl: string;
  features: Features;
  defaultSource: string;
  chartOptions: ChartOptions;
  tableOptions: TableOptions;
  ui: UIConfig;
}

type ConfigFile = Record<Environment, Partial<Config>>;

// Type the imported JSON
const config = rawConfig as ConfigFile;

const environment: Environment = import.meta.env.PROD ? 'production' : 'development';

const defaultConfig: Config = {
  apiBaseUrl: '',
  wsBaseUrl: '',
  features: {
    enableCharts: false,
    enableRealtime: false,
    enableDataSources: [],
  },
  defaultSource: '',
  chartOptions: {
    width: 800,
    height: 600,
    theme: 'light',
    colors: [],
    animation: false,
  },
  tableOptions: {
    pageSize: 10,
    sortable: false,
    filterable: false,
    exportable: false,
  },
  ui: {
    theme: 'light',
    primaryColor: '#000000',
    fontSize: '16px',
    fontFamily: 'Arial, sans-serif',
  },
};

const currentConfig: Config = {
  ...defaultConfig,
  ...(config[environment] || {}),
  features: {
    ...defaultConfig.features,
    ...(config[environment]?.features || {}),
  },
  chartOptions: {
    ...defaultConfig.chartOptions,
    ...(config[environment]?.chartOptions || {}),
  },
  tableOptions: {
    ...defaultConfig.tableOptions,
    ...(config[environment]?.tableOptions || {}),
  },
  ui: {
    ...defaultConfig.ui,
    ...(config[environment]?.ui || {}),
  },
};

export const AppConfig = {
  ...currentConfig,
  isProduction: environment === 'production',
  isDevelopment: environment === 'development',

  // Helper methods
  getApiUrl: (path: string) => `${currentConfig.apiBaseUrl}${path}`,
  getWsUrl: (path: string) => `${currentConfig.wsBaseUrl}${path}`,
  isFeatureEnabled: (feature: keyof Features) => currentConfig.features[feature],

  // Constants
  API_ENDPOINTS: {
    CHAT: '/chat',
    SEARCH: '/search',
    DATA_SOURCES: '/data-sources',
  },
};

export default AppConfig;
