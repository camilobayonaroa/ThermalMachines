% LS.cls
\usepackage[spanish,es-tabla]{babel}
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{LS}
% Initial Statements
\usepackage{float}
\usepackage{tikz}
\addto\captionsspanish{\renewcommand{\abstractname}{Abstract}}


% Inside your custom class file (.cls)

\RequirePackage{etoolbox} % Load the etoolbox package for \AtBeginEnvironment command

% Adjust the font size for table content
\AtBeginEnvironment{tabular}{\small} % Set font size to \small (size 9)

% You can also adjust the vertical spacing in tables using \renewcommand{\arraystretch}
\renewcommand{\arraystretch}{1.2} % Adjust vertical spacing in tables if needed
\setlength{\abovedisplayskip}{1pt} % Espacio antes de la ecuación
\setlength{\belowdisplayskip}{1pt}

% Language Statements
\newif\iflang@eng
\newif\iflang@por
\def\lang@mutopterr{%
    \PackageError{lang}{Options 'eng' and 'por' are mutually exclusive.}{}%
}%
\DeclareOption{eng}{%
    \iflang@por\lang@mutopterr\fi
    \lang@engtrue\lang@porfalse
}
\DeclareOption{por}{%
    \iflang@eng\lang@mutopterr\fi
    \lang@engfalse\lang@portrue
}

\ProcessOptions\relax

% Load necessary packages
\RequirePackage[utf8]{inputenc}
\RequirePackage[english]{babel}
\RequirePackage{ifthen}
\RequirePackage{calc}
\AtEndOfClass{\RequirePackage{microtype}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions*
\LoadClass{article}
\RequirePackage{times}      % Loads the Times-Roman Fonts
\RequirePackage{mathptmx}   % Loads the Times-Roman Math Fonts
\RequirePackage{ifpdf}
\RequirePackage{amsmath,amsfonts,amssymb}
\RequirePackage{graphicx,xcolor}
\RequirePackage{booktabs}
\RequirePackage{authblk}
\RequirePackage[left=1.5cm,right=1.5cm,top=1.5cm,bottom=1.5cm,headheight=12pt,letterpaper]{geometry}

\RequirePackage[labelfont={bf,sf},labelsep=period,justification=raggedright]{caption}
\RequirePackage[colorlinks=true, allcolors=black]{hyperref}
\usepackage{graphicx}
\usepackage{subcaption}
\usepackage{amsmath}


\usepackage{enumitem}
% Define the @coauthor command
\newcommand{\@coauthor}[1]{%
  {\centering\fontsize{8}{12}\selectfont #1\par}% <-- Changed
}

% Define the @maketitle command
\renewcommand{\@maketitle}{%
{%
\thispagestyle{empty}%

\vskip-36pt%

{\includegraphics[width = 25mm]{JaveLogo.png}}
{\begin{flushright}
\vskip-64pt 
\textit{\fontsize{14}{16}\selectfont Facultad de Ingeniería} \\
\textit{\fontsize{18}{20}\selectfont DPTO INGENIERÍA INDUSTRIAL} \\
\textit{\fontsize{9}{11}\selectfont Coordinación de Proyectos y Trabajos de Grado\\
}
\end{flushright}}

\vskip10pt
{\centering\fontsize{17}{30}\selectfont \@title\par}% Title in 17pt size

\vskip10pt
{\centering\fontsize{13}{5}\selectfont  \@author\par}% Authors in 13pt size

\vskip10pt
{\centering\fontsize{11}{6}\selectfont  
\textsuperscript{\textsuperscript{\textit{a}} \textit{Estudiante de Ingeniería Mecánica
}} \\
  \textsuperscript{\textsuperscript{\textit{b}} \textit{Profesor, Director del Trabajo de Grado, Departamento de IngenierIndustriíal}} \\
    \textsuperscript{\textsuperscript{\textit{c}} \textit{Profesor, Codirector del Trabajo de Grado, Departamento de Ingeniería Industrial
}} \\
  \textsuperscript{\textsuperscript{\textit{d}} \textit{Pontificia Universidad Javeriana, Bogotá, Colombia}} \\
\par}
}%
}%


% Redefine section command
\renewcommand{\section}{%
    \@startsection%
        {section}%                       % level
        {1}%                             % depth
        {0mm}%                           % indent
        {-\baselineskip}%                % before skip
        {0.05\baselineskip}%              % after skip
        {\bfseries\fontsize{10}{12}\selectfont}%  % style
}
% Redefine subsection command
\renewcommand{\subsection}{%
    \@startsection%
        {subsection}%                          % level
        {1}%                                   % depth
        {0mm}%                                 % indent
        {-\baselineskip}%                      % before skip
        {0.05\baselineskip}%                    % after skip
        {\bfseries\fontsize{10}{12}\selectfont}% % style
}

% Configuration of figure headings
\usepackage{caption}
\captionsetup[figure]{font=small,labelfont=bf,justification=centering}
\captionsetup[figure]{name=Fig.}
\DeclareCaptionFormat{myformat}{#1#2#3}%\rule{\linewidth}{.3pt}}
\captionsetup[figure]{format=myformat}

\captionsetup[table]{font={small,sc},labelfont={bf,sc},justification=centering}
\iflang@eng
  \captionsetup[table]{name=Table}
\fi
\iflang@por
  \captionsetup[table]{name=Tabela}
  \captionsetup[figure]{name=Figura}
\fi
\usepackage{makecell} % break lines in cell tables
\renewcommand\theadalign{cc}
\renewcommand\theadgape{\Gape[4pt]}
\renewcommand\cellgape{\Gape[4pt]}
\addtolength{\belowcaptionskip}{-8pt}
\addtolength{\abovecaptionskip}{0pt}
% Default language: English
  \iflang@eng
  \else
    \iflang@por
    \else
      \lang@engtrue\lang@porfalse
    \fi
  \fi

% Set bibliography style
\usepackage[natbibapa]{apacite}
\bibliographystyle{apacite}

\newcommand{\quotes}[1]{`#1''}

\newcommand{\insertbibliography}[1]{%
  \setlength{\parindent}{0pt}
  {\setstretch{0.5}
  \fontsize{8}{10}\selectfont
  \iflang@eng
    \renewcommand\refname{References}
  \fi
  \bibliography{#1}}
}

% Increase spacing between paragraphs
\setlength{\parskip}{0.25em}