import Highcharts from 'highcharts'
import HighchartsReact from 'highcharts-react-official'




interface PieChartProps {
  data: {
    seriesNames: string[];  // nomes das séries/fatias, ex: ["Usina A", "Usina B"]
    values: number[];       // valores correspondentes
  };
}
function Pie({data}: PieChartProps){
  const seriesData = data.seriesNames.map((name, i) => ({
    name,
    y: data.values[i]
  }));
      const options = {
    chart: {
      type: 'pie',
      width: 600,
      height: 300,
      backgroundColor: null
    },
    title: {
      text: '',
      style: {
        color: '#FFF'
      }
    },
    series: [
      {
        name: 'Distribuição',
        colorByPoint: true,
        data: seriesData
      }
    ],
    credits: {
      enabled: false
    }
  };
    return (
    <HighchartsReact
      highcharts={Highcharts}
      options={options}
    />
  );
}






export default Pie
