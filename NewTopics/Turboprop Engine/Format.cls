\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{LS}
% Initial Statements
\usepackage{float}
\usepackage{tikz}



% Inside your custom class file (.cls)

\RequirePackage{etoolbox} % Load the etoolbox package for \AtBeginEnvironment command

% Adjust the font size for table content
\AtBeginEnvironment{tabular}{\small} % Set font size to \small (size 9)

% You can also adjust the vertical spacing in tables using \renewcommand{\arraystretch}
\renewcommand{\arraystretch}{1.2} % Adjust vertical spacing in tables if needed


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
\RequirePackage[left=2.5cm,right=2cm,top=2.25cm,bottom=2.25cm,headheight=12pt,letterpaper]{geometry}
\RequirePackage[labelfont={bf,sf},labelsep=period,justification=raggedright]{caption}
\RequirePackage[colorlinks=true, allcolors=blue]{hyperref}
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
\textit{\fontsize{14}{16}\selectfont School of Engineering} \\
\textit{\fontsize{18}{20}\selectfont Mechanical Engineer} \\
\textit{\fontsize{9}{11}\selectfont Degree Project - Second Semester 2024\\
}
\end{flushright}}

\vskip10pt
{\centering\fontsize{17}{30}\selectfont \@title\par}% Title in 17pt size

\vskip10pt
{\centering\fontsize{13}{5}\selectfont  \@author\par}% Authors in 13pt size

\vskip10pt
{\centering\fontsize{8}{6}\selectfont  
\textsuperscript{\textit{a} \textit{Mechanical Engineering Student}} \\

  \textsuperscript{\textit{b} \textit{Professor, Project Director, Department of Industrial Engineering}} \\
  \textsuperscript{\textit{c} \textit{Pontificia Universidad Javeriana, Bogotá, Colombia}} \\
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
        {0.5\baselineskip}%              % after skip
        {\bfseries\fontsize{10}{12}\selectfont}%  % style
}
% Redefine subsection command
\renewcommand{\subsection}{%
    \@startsection%
        {subsection}%                          % level
        {2}%                                   % depth
        {0mm}%                                 % indent
        {-\baselineskip}%                      % before skip
        {0.5\baselineskip}%                    % after skip
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
\usepackage[numbers]{natbib} % Use numbers style for IEEE
\bibliographystyle{IEEEtran} % Use IEEEtran bibliography style

\newcommand{\quotes}[1]{``#1''}

\newcommand{\insertbibliography}[1]{%
  \setlength{\parindent}{0pt}
  {\setstretch{0.85}
  \fontsize{8}{10}\selectfont
  \iflang@eng
    \renewcommand\refname{References}
  \fi
  \bibliography{#1}}
}

% Increase spacing between paragraphs
\setlength{\parskip}{1em}