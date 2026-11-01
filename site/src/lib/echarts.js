/**
 * Registro mínimo do ECharts (tree-shaking). Este módulo é importado de forma
 * dinâmica por grafico.js/mapa.js — o ECharts só é baixado quando o primeiro
 * gráfico entra na tela.
 *
 * Precisa de outro tipo de gráfico/componente? Importe e acrescente em `use([...])`.
 * Lista: https://echarts.apache.org/handbook/en/basics/import
 */
import * as echarts from 'echarts/core';
import {
  BarChart, LineChart, ScatterChart, MapChart, HeatmapChart, BoxplotChart, CustomChart, PieChart, SankeyChart,
} from 'echarts/charts';
import {
  GridComponent, TooltipComponent, LegendComponent, TitleComponent, DatasetComponent,
  TransformComponent, DataZoomComponent, MarkLineComponent, MarkAreaComponent, MarkPointComponent,
  VisualMapComponent, GeoComponent, AriaComponent, GraphicComponent,
} from 'echarts/components';
import { LabelLayout, UniversalTransition } from 'echarts/features';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart, LineChart, ScatterChart, MapChart, HeatmapChart, BoxplotChart, CustomChart, PieChart, SankeyChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent, DatasetComponent,
  TransformComponent, DataZoomComponent, MarkLineComponent, MarkAreaComponent, MarkPointComponent,
  VisualMapComponent, GeoComponent, AriaComponent, GraphicComponent,
  LabelLayout, UniversalTransition, CanvasRenderer,
]);

export default echarts;
