export const getChartTheme = (isDark: boolean) => ({
  text: isDark ? '#e5e7eb' : '#374151',
  grid: isDark ? '#374151' : '#e5e7eb',
  tooltipBg: isDark ? '#111827' : '#ffffff',
  tooltipBorder: isDark ? '#4b5563' : '#d1d5db',
})