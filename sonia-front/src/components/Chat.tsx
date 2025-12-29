import { useState } from "react";
import SidebarEsquerda from './SidebarEsquerda';
import ChatCentral from './ChatCentral';
import SidebarDireita from './SidebarDireita';

interface Font {

  path: string;
}

export default function ChatUI() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isShowSidebarDireita, setIsShowSidebarDireita] = useState(false);

  // estado das fontes
  const [fonts, setFonts] = useState<Font[]>([]);
  const [fontsHistory, setFontsHistory] = useState<Font[]>([]);

  return (
    <div className="min-h-screen flex flex-col md:flex-row font-montserrat bg-[#F7F6F6]">
      {/* Sidebar esquerda */}
      <SidebarEsquerda messages={messages} fonts={fontsHistory} />

      {/* Chat central */}
      <div className="flex-1 flex">
        <ChatCentral
          showSidebar={setIsShowSidebarDireita}
          messages={messages}
          setMessages={setMessages}
          setFonts={setFonts}
          setFontsHistory={setFontsHistory}
          fontsHistory={fontsHistory}
        />
      </div>

      {/* Sidebar direita controlada pelo estado */}
      <SidebarDireita
        isShow={isShowSidebarDireita}
        setIsShow={setIsShowSidebarDireita}
        fonts={fonts}
      />
    </div>
  );
}
