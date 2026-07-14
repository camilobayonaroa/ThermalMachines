function p = default_params()
% DEFAULT_PARAMS — Motor RAMJET de tesis, M_inf=2.0 a 10 km ISA

% --- Longitudes (m) ---
p.l1 = 0.20;   % precono (antes del labio)
p.l2 = 0.22;   % difusor externo / labio
p.l3 = 0.32;   % difusor interno (ducto)
p.l4 = 0.38;   % camara de combustion
p.l5 = 0.14;   % convergente tobera
p.l6 = 0.24;   % divergente tobera

% --- Radios coraza (m) ---
p.rc      = 0.082;   % radio camara  (Ø164 mm)
p.rcd     = 0.046;   % radio garganta (Ø92 mm)
p.re_exit = 0.092;   % radio salida  (Ø184 mm)

% --- Labio ---
p.xlip_frac = 0.22;
p.g_lip     = 0.024;   % gap labio-spike en xlip (24 mm)
p.r_inlet   = 0.096;   % radio coraza en x2

% --- Spike ---
% ri_peak=0.058 con r_inlet=0.096 garantiza gap ~25mm en el pico
p.ri_x1   = 0.004;
p.ri_peak = 0.058;
p.xm_frac = 0.42;

% --- Discretizacion ---
p.N    = 2000;
p.gmin = 0.013;   % solo para verificacion

% --- Termodinamica ISA 10 km ---
p.M_inf   = 2.0;
p.T_inf   = 223.15;
p.P_inf   = 26500;
p.rho_inf = 0.4135;
p.R       = 287.05;
p.gamma   = 1.4;
p.Cp      = p.gamma * p.R / (p.gamma - 1);
p.LHV     = 43.0e6;
p.f       = 0.030;
p.eta_d   = 0.92;
p.eta_c   = 0.98;
p.eta_n   = 0.96;
end

%[appendix]{"version":"1.0"}
%---
