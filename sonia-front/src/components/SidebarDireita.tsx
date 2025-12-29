import { CaretLeft, CaretRight } from "@phosphor-icons/react";

interface Font {
  path: string;
}

interface SidebarProps {
  isShow: boolean;
  setIsShow: React.Dispatch<React.SetStateAction<boolean>>;
  fonts: Font[];
}

export default function SidebarDireita({ isShow, setIsShow, fonts }: SidebarProps) {
  return (
<aside
  className={`
    hidden md:flex md:flex-col md:h-screen md:border-l md:bg-white
    transition-all duration-300 ease-in-out
    ${isShow ? "md:w-80" : "md:w-0 overflow-hidden"}
    relative
  `}
>
  {/* Botão de abrir/fechar sempre renderizado no desktop */}
  <button
    className="absolute -left-9 top-3 px-2 py-2 bg-amber-700 text-white rounded-l cursor-pointer flex items-center justify-center z-10"
    onClick={() => setIsShow(!isShow)}
  >
    {isShow ? <CaretRight size={20} weight="bold" /> : <CaretLeft size={20} weight="bold" />}
  </button>

  {/* Conteúdo só aparece quando aberto */}
  {isShow && (
    <>
      <div className="px-4 py-4 border-b flex items-center justify-between">
        <h3 className="font-semibold text-[#090A59] text-sm">Bases Relacionadas {"("+fonts.length+")"}</h3>
        <a href="https://dados.ons.org.br/">
          <span className="text-xs text-blue-500 cursor-pointer">Ver Base Central</span>
        </a>
      </div>

      <nav className="flex-1 overflow-auto p-4 space-y-4">
        <ul className="space-y-3 w-full">
            {fonts.map((font, index) => (
              <li
                key={index}
                className="mb-4 p-2 rounded-md hover:bg-gray-50 cursor-pointer border w-full"
              >
                <div className="text-xs font-bold text-[#002246] break-words">{font.path}</div>
              </li>
            ))}
          </ul>
      </nav>
    </>
  )}
</aside>

  );
}
