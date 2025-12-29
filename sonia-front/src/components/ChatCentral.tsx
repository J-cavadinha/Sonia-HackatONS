import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import Pie from "./Piechart";
import Bar from "./Barchart";
import Line from "./Linechart";
import Scatter from "./Scatterchart";
import api from '../services/api';

interface Message {
  id: number;
  from: 'bot' | 'user';
  text: string,
  chartType?: "bar" | "scatter" | "pie" | "line";
  data?: unknown;
  isLoading?: boolean;
}

interface Font {
  id: number;
  name: string;
  description: string;
  link: string;
}

interface Props {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  showSidebar: React.Dispatch<React.SetStateAction<boolean>>;
  setFonts: React.Dispatch<React.SetStateAction<Font[]>>;
  setFontsHistory: React.Dispatch<React.SetStateAction<Font[]>>;
  fontsHistory: Font[]
}

export default function ChatCentral({ showSidebar, messages, setMessages, setFonts, setFontsHistory, fontsHistory }: Props) {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [placeholder, setPlaceholder] = useState('Digite uma mensagem...');
  const messagesRef = useRef<HTMLDivElement | null>(null);

  // MONTAR COM PERGUNTAS POSSIVEIS
  const placeholders = [
    "Qual a usina mais ao sul do mundo?",
    "O que você faz?",
    ""
  ];
  // const question = "Retorne um gráfico de barras com a geração de energia por região em 2025"


  useEffect(() => {
    const random = Math.floor(Math.random() * placeholders.length);
    setPlaceholder(placeholders[random]);
  }, []);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [messages]);

  async function handleSend() {

    const text = input.trim();
    if (!text || isSending) return;

    setIsSending(true);
    const userMessage: Message = { id: Date.now(), from: 'user', text };
    setMessages((m) => [...m, userMessage])

    // Add loading message
    const loadingMessage: Message = {
      id: Date.now() + 0.5,
      from: 'bot',
      text: 'Pensando...',
      isLoading: true
    };
    setMessages((m) => [...m, loadingMessage]);

    const arrHist = []
    const context = JSON.stringify(
      messages.map(msg => ({ from: msg.from, text: msg.text, chart: msg.chartType, chartData: msg.data }))
    );
    arrHist.push(context)
    setInput('');

    try {
      const req = await api.post("/analyze", { question: text, chat_history: [] });
      const { response, chart, data_points } = req.data;
      console.log(req.data)

      // Remove loading message and add bot response
      setMessages((m) => m.filter(msg => msg.id !== loadingMessage.id));

      const botMessage: Message = {
        id: Date.now() + 1,
        from: "bot",
        text: response,
        chartType: chart,
        data: data_points
      };

      setMessages((m) => [...m, botMessage]);

      if (req.status === 200) {
        // Set fonts from the response if available
        if (req.data.datasets_consumed) {
          const fontsArray = req.data.datasets_consumed.map((dataset: any) => ({
            path: dataset.path
          }));

          setFontsHistory((prev) => {
            const merged = [...prev, ...fontsArray];
            const unique = merged.filter(
              (font, index, self) =>
                index === self.findIndex((f) => f.path === font.path)
            );
            return unique;
          });

          setFonts(fontsArray);
          showSidebar(true);
        }
      } else {
        // Remove loading message and add error message
        setMessages((m) => m.filter(msg => msg.id !== loadingMessage.id));
        const errorMessage: Message = {
          id: Date.now() + 2,
          from: 'bot',
          text: `Houve um problema de comunicação com servidor (status: ${req.status}). Tente novamente mais tarde.`
        };
        setMessages((m) => [...m, errorMessage]);
      }

    } catch (e: any) {
      // Remove loading message and add error message
      setMessages((m) => m.filter(msg => msg.id !== loadingMessage.id));
      const errorMessage: Message = {
        id: Date.now() + 3,
        from: 'bot',
        text: `No momento não consegui me conectar ao servidor. Tente novamente mais tarde. Razão: ${e.message || e}`
      };
      setMessages((m) => [...m, errorMessage]);
    } finally {
      setIsSending(false);
    }
  }


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


  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // Função para renderizar texto com formatação Markdown (negrito)
  function renderFormattedText(text: string) {
    // Divide o texto em partes, alternando entre texto normal e texto em negrito
    const parts = text.split(/(\*\*.*?\*\*)/g);

    return parts.map((part, index) => {
      // Se a parte começa e termina com **, renderiza em negrito
      if (part.startsWith('**') && part.endsWith('**')) {
        const boldText = part.slice(2, -2); // Remove os ** do início e fim
        return <strong key={index}>{boldText}</strong>;
      }
      // Caso contrário, renderiza texto normal
      return <span key={index}>{part}</span>;
    });
  }

  return (
    <main className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-4 md:px-6 py-4 border-b bg-white">
        <h2 className="text-lg font-semibold text-[#090A59]">
          O que você quer saber dos dados públicos ONS?
        </h2>
      </header>

      {/* Mensagens */}
      <div className="flex-1 overflow-auto p-4 md:p-6 bg-[#F3F7FA]" ref={messagesRef}>
        <div className="max-w-3xl mx-auto flex flex-col gap-4">
          {messages.map((m) => (
            <div key={m.id} className={m.from === 'user' ? 'flex justify-end' : 'flex justify-start'}>
              {m.from === 'bot' && (
                <div className="flex items-start gap-3">
                  <img
                    src="/assistant.png"
                    alt="Assistant"
                    className="w-8 h-8 rounded-full flex-shrink-0 mt-1"
                  />
                  <div
                    className="p-3 rounded-lg max-w-[80%] break-words shadow-sm"
                    style={{
                      backgroundColor: '#FFFFFF',
                      color: '#0f172a',
                      border: '1px solid rgba(2,34,70,0.06)',
                      fontSize: 16,

                    }}
                  >
                    <span className={m.isLoading ? 'animate-pulse' : ''}>
                      {renderFormattedText(m.text)}
                    </span>
                    {m.chartType && (
                      <div className="mt-2" style={{ overflowX: "auto" }}>
                        <div style={{ minWidth: "600px" }}>
                          {renderChart(m.chartType, m.data)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {m.from === 'user' && (
                <div
                  className="p-3 rounded-lg max-w-[80%] break-words shadow-sm"
                  style={{
                    backgroundColor: '#002A75',
                    color: '#FFFFFF',
                    border: '1px solid rgba(0,0,0,0.04)',
                    fontSize: 16,
                  }}
                >
                  {renderFormattedText(m.text)}
                </div>
              )}
            </div>
          ))}

          <div className="flex flex-col items-center justify-center mt-6 text-xs text-gray-500 text-center">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center">
                <img src="/assistant.png" className="w-16 h-16 mb-2 mt-[70%]" alt="Logo S.O.N.I.A" />
                <p>Comece a conversa para ver as mensagens aqui.</p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center">
                <p>Fim da conversa. Lembre-se de que esse diálogo não fica salvo.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Input */}
      <div className="px-4 md:px-6 py-4 border-t bg-white">
        <div className="max-w-3xl mx-auto flex flex-col md:flex-row gap-3">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder} // placeholder dinâmico
            className="flex-1 resize-none rounded-md border px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#002246]"
            style={{ minHeight: 48 }}
            disabled={isSending}
          />
          <button
            onClick={handleSend}
            disabled={isSending}
            className={`w-full md:w-auto px-4 py-2 rounded-md text-white font-semibold transition ${isSending ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#F94300] hover:opacity-95'
              }`}
          >
            {isSending ? 'Enviando...' : 'Enviar'}
          </button>
        </div>
      </div>

    </main>
  );
}
