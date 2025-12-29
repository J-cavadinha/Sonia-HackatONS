import { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import html2canvas from "html2canvas";
import  Pie  from "./components/Piechart";
import  Bar  from "./components/Barchart";
import  Line  from "./components/Linechart";
import  Scatter  from "./components/Scatterchart";

interface Props {
  messages: object[];
  fonts: object[];
}

export default function SidebarEsquerda({ messages, fonts }: Props) {
  const [isExporting, setIsExporting] = useState(false);


  function renderChart(chartType?: string, data?: Array<number>) {
      switch (chartType) {
        case "bar":
          return <Bar data={data} />;
        case "scatter":
          return <Scatter data={data} />;
        case "pie":
          return <Pie data={data} />;
        case "line":
          return <Line data={data} />;
        default:
          return null; 
      }
    }
const handleExport = async () => {
  setIsExporting(true);
  try {
    const doc = new jsPDF();

    // Cabeçalho
    doc.setFontSize(18);
    doc.setTextColor("#090A59");
    doc.text("Conversa com S.O.N.I.A", 14, 20);

    doc.setFontSize(11);
    doc.setTextColor(100);
    doc.text(`Exportado em ${new Date().toLocaleString("pt-BR")}`, 14, 28);

    doc.addImage("/assistant.png", "PNG", 170, 10, 30, 30);

    let graphIndex = 1;
    const graphRefs: { msg: any; imgData: string; label: string }[] = [];

    // Prepara linhas da tabela de mensagens
    const rows = messages.map((msg: any) => {
      if (msg.chartType !== "False" && msg.data) {
        const label = `[Gráfico ${graphIndex}]`;
        graphIndex++;
        return [
          msg.from === "user" ? "Usuário" : "S.O.N.I.A",
          (msg.text || "") + " " + label,
        ];
      }
      return [msg.from === "user" ? "Usuário" : "S.O.N.I.A", msg.text || ""];
    });

    // Renderiza tabela de mensagens
    autoTable(doc, {
      startY: 40,
      head: [["Remetente", "Mensagem"]],
      body: rows,
      theme: "striped",
      styles: { fontSize: 10, cellPadding: 4 },
      headStyles: { fillColor: [9, 10, 89] },
    });

    // Renderiza gráficos temporariamente e guarda referência
    graphIndex = 1;
    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      if (msg.chartType !== "False" && msg.data) {
        const tempDiv = document.createElement("div");
        tempDiv.style.position = "absolute";
        tempDiv.style.left = "-9999px";
        document.body.appendChild(tempDiv);

        const ChartJSX = renderChart(msg.chartType, msg.data);
        const { createRoot } = await import("react-dom/client");
        const root = createRoot(tempDiv);
        root.render(ChartJSX);

        // Aguarda renderização completa
        await new Promise((r) => setTimeout(r, 1500));

        // Captura canvas
        const canvas = await html2canvas(tempDiv, { scale: 0.7 });
        const imgData = canvas.toDataURL("image/png");

        if (imgData.startsWith("data:image/png")) {
          graphRefs.push({
            msg,
            imgData,
            label: `Gráfico ${graphIndex}`,
          });
          graphIndex++;
        } else {
          console.error("Imagem do gráfico inválida", msg);
        }

        root.unmount();
        tempDiv.remove();
      }
    }

    // Pega posição final da tabela
    let finalY = (doc as any).lastAutoTable.finalY || 40;

    // Tabela de fontes
    const rows2 = fonts.map((font: any) => [font.path]);
    autoTable(doc, {
      startY: finalY + 10,
      head: [["Fontes Utilizadas"]],
      body: rows2,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 4 },
      headStyles: { fillColor: [249, 67, 0] },
    });

    finalY = (doc as any).lastAutoTable.finalY + 10;

    // Se houver gráficos, cria seção
    if (graphRefs.length > 0) {
      doc.addPage();
      doc.setFontSize(16);
      doc.setTextColor("#090A59");
      doc.text("Gráficos", 14, 20);

      let y = 30;
      for (const g of graphRefs) {
        if (y + 100 > 280) {
          doc.addPage();
          y = 20;
        }

        doc.setFontSize(12);
        doc.setTextColor(0);
        doc.text(g.label, 14, y);
        y += 5;

        // Cria imagem temporária e espera carregar
        const tempImg = new Image();
        tempImg.src = g.imgData;
        await new Promise((res) => (tempImg.onload = res));

        const aspectRatio = tempImg.width / tempImg.height;
        const pdfWidth = 180;
        const pdfHeight = pdfWidth / aspectRatio;

        doc.addImage(g.imgData, "PNG", 14, y, pdfWidth, pdfHeight);
        y += pdfHeight + 10;
      }
    }

    doc.save("conversa.pdf");
  } finally {
    setTimeout(() => setIsExporting(false), 800);
  }
};


  return (
    <aside className="w-full md:w-72 border-r flex flex-col bg-white h-fit md:h-screen ">
      {/* Cabeçalho */}
      <div className="px-4 py-6 flex items-center gap-3 border-b">
        <div className="w-20 h-20 rounded flex items-center justify-center text-white font-bold">
          <img src="/assistant.png"></img>
        </div>
        <div>
          <div className="text-[#090A59] font-bold">S.O.N.I.A</div>
          <div className="text-xs text-[#002246]">
            Sistema do Operador Nacional para Informação Acessível
          </div>
        </div>
      </div>

      {/* Conteúdo principal */}
      <div className="p-4 flex-1"></div>

      {/* Botão exportar */}
      <div className="px-4 pb-4">
        <button
          className="w-full cursor-pointer py-2 rounded-md text-white font-semibold shadow-sm 
                     bg-[#F94300] hover:bg-[#d43400] 
                     disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          disabled={messages.length === 0 || isExporting}
          onClick={handleExport}
        >
          {isExporting ? (
            <>
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                ></path>
              </svg>
              Exportando...
            </>
          ) : (
            "Exportar Conversa"
          )}
        </button>
      </div>

      {/* Rodapé */}
      <div className="px-4 py-2 border-t text-xs text-gray-500">
        Agente S.O.N.I.A • v1.0.0 • Protótipo
      </div>
    </aside>
  );
}
