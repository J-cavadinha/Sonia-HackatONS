import Highcharts from 'highcharts'
import HighchartsReact from 'highcharts-react-official'




interface BarProps {
  data: {
    seriesNames: string[];   // nomes das séries, ex: ["Usina A", "Usina B"]
    labels: string[];        // categorias do eixo X, ex: ["Jan", "Fev"]
    data: number[][];      // array de arrays: cada subarray = dados da série correspondente
  };
}

function Bar({ data }: BarProps){
 const series = data.seriesNames.map((name, i) => ({
  name,
  data: data.data[i], 
}));

      const options = {
    chart: {
      type: 'column',
      
      height: 300,
      backgroundColor: null
    },
    title: {
      text: '',
      style: {
        color: '#FFF'
      }
    },
    xAxis: { categories: data.labels },
    yAxis: { title: { text: '' } },
    series: series,
    // series: [{
    //   name: [data.labels], 
    //   colorByPoint: true, 
    //   data: [data.data], 
    // }],
    // credits: {
    //   enabled: false
    // }
  };
    return (
    <HighchartsReact
      highcharts={Highcharts}
      options={options}
    />
  );
}


export default Bar