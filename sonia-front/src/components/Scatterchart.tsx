import React from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';

interface ScatterChartProps {
  data: {
    seriesNames: string[];        // nomes das séries
    values: [number, number][][]; // array de arrays de pontos [x, y] por série
  };
}

function Scatter({ data }: ScatterChartProps) {
  // Cria séries para Highcharts
  const series = data.seriesNames.map((name, i) => ({
    name,
    type: 'scatter',
    colorByPoint: true,
    data: data.values[i] || []
  }));

  const options = {
    chart: {
      type: 'scatter',
      backgroundColor: 'transparent',
      zoomType: 'xy',
    },
    title: {
      text: 'Análise de Dispersão de Dados',
      align: 'left',
      style: {
        fontSize: '18px',
        color: '#1f2937'
      }
    },
    xAxis: {
      title: { text: 'Eixo X: Variável Independente' },
      startOnTick: true,
      endOnTick: true,
      showLastLabel: true,
      style:{
        width: "fit-content"
      }
    },
    yAxis: {
      title: { text: 'Eixo Y: Variável Dependente' }
    },
    legend: { enabled: true },
    plotOptions: {
      scatter: {
        marker: {
          radius: 5,
          states: { hover: { enabled: true, lineColor: 'rgb(100,100,100)' } }
        },
        tooltip: {
          headerFormat: '<b>{series.name}</b><br>',
          pointFormat: 'Valor X: {point.x}, Valor Y: {point.y}'
        }
      }
    },
    series,
    credits: { enabled: false }
  };

  return (
    <div >
   

        <HighchartsReact highcharts={Highcharts} options={options} />

      
    </div>
  );
}

export default Scatter;
