import React from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";

interface LineProps {
  data: {
    seriesName: string;             // Nome da série (ex: "Evolução das usinas")
    labels: string[];               // Categorias no eixo X (ex: ["Usina1", "Usina2"])
    data: { x: number; y: number }[]; // Dados: x será o índice da usina, y o valor
  };
}

export default function Line({ data }: LineProps) {
  const { seriesName, labels, data: points } = data;

  // Mapeia os pontos recebidos para garantir que X corresponda ao índice da label
  const normalized = points.map((point, i) => ({
    x: i,
    y: point.y
  }));

  const options: Highcharts.Options = {
    chart: {
      type: "line",
      width: 600,
      height: 300,
      backgroundColor: "transparent"
    },
    title: { text: "" },
    xAxis: {
      categories: labels,
      title: { text: "Usinas" }
    },
    yAxis: {
      title: { text: "Evolução" }
    },
    series: [
      {
        name: seriesName,
        type: "line",
        data: normalized
      }
    ],
    credits: { enabled: false }
  };

  return <HighchartsReact highcharts={Highcharts} options={options} />;
}
