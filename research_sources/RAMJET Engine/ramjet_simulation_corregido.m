%% RAMJET_SIMULATION_CORREGIDO
% Modelo RAMJET 1D estable para tesis:
% 1) Geometria parametrizable con A(x) suave por Hermite.
% 2) dA/dx analitica y continua por construccion.
% 3) Difusor y tobera resueltos con relacion area-Mach, sin cruzar M=1 con ODE45.
% 4) Tobera C-D choked: M=1 en la garganta y rama supersonica en el divergente.
%
% NOTA IMPORTANTE:
% La version anterior se podia quedar pegada porque integraba con ode45
% la ecuacion dM/dx ~ 1/(1-M^2) dentro de la tobera. En la garganta
% M -> 1 y la ecuacion se vuelve singular. Por eso aqui la tobera se
% resuelve algebraicamente por ramas subsonica/supersonica.

clear; clc; close all;

%% 1) PARAMETROS Y GEOMETRIA
p = default_params();
[A, re_plot, ri, x, dAdx, st, re_flow, xlip] = ramjet_geometry(p);

R     = p.R;
gamma = p.gamma;
Cp    = p.Cp;

a = (gamma-1)/2;

%% 2) INTERPOLADORES DE GEOMETRIA
mask = ~isnan(A);
[xd, ia] = unique(x(mask),'stable');
Ad   = A(mask);    Ad   = Ad(ia);
dAd  = dAdx(mask); dAd  = dAd(ia);

A_fun    = @(xq) max(interp1(xd,Ad,  xq,'pchip','extrap'),1e-8);
dAdx_fun = @(xq)     interp1(xd,dAd, xq,'pchip','extrap');

%% 3) CONDICIONES DE VUELO LIBRE
Ma    = p.M_inf;
Ta    = p.T_inf;
Pa    = p.P_inf;
rho_a = Pa/(R*Ta);
ua    = Ma*sqrt(gamma*R*Ta);

T0_inf = Ta*(1+a*Ma^2);
P0_inf = Pa*(1+a*Ma^2)^(gamma/(gamma-1));

fprintf('\n=== FLUJO LIBRE ===\n');
fprintf('  Ma = %.3f\n',Ma);
fprintf('  Ta = %.2f K     Pa = %.2f kPa     rho_a = %.4f kg/m3\n',Ta,Pa/1e3,rho_a);
fprintf('  ua = %.2f m/s   T0,a = %.2f K     P0,a = %.2f kPa\n',ua,T0_inf,P0_inf/1e3);

%% 4) RECUPERACION DEL DIFUSOR / ENTRADA AL DUCTO
% Despues del sistema de choques se considera flujo subsonico en el ducto.
% P02 incluye la recuperacion de presion total del inlet/difusor externo.
T02 = T0_inf;
P02 = p.eta_d * P0_inf;

%% 5) CAMARA: T0 sube por combustion y P0 cae por perdidas
% Se usa f respecto al flujo de aire: mdot_f = f * mdot_air.
% La presion total de salida de camara se modela con sigma_b, no con eta_b.
T04 = T02 + (p.f*p.eta_b*p.LHV)/((1+p.f)*Cp);
P04 = p.sigma_b * P02;

%% 6) FLUJO MASICO CONSISTENTE CON TOBERA CHOKED
% Para evitar inconsistencias numericas, el flujo masico se calcula desde
% la garganta. Esto representa que la tobera fija el caudal admisible.
A5      = A_fun(st.x5);
mfpStar = mass_flow_parameter(1,gamma,R);
mg_dot  = P04*A5/sqrt(T04)*mfpStar;  % gases despues de combustion
m_dot   = mg_dot/(1+p.f);            % aire antes de inyectar combustible
mf_dot  = p.f*m_dot;

fprintf('\n=== FLUJO MASICO DE DISENO ===\n');
fprintf('  A_garganta = %.6f m2\n',A5);
fprintf('  mdot aire  = %.4f kg/s\n',m_dot);
fprintf('  mdot fuel  = %.4f kg/s\n',mf_dot);
fprintf('  mdot gases = %.4f kg/s\n',mg_dot);

%% 7) DIFUSOR INTERNO x2 -> x3
% En el difusor se conserva T0 y P0. M se obtiene de la relacion area-Mach
% para la rama subsonica, compatible con el flujo masico calculado.
N_diff = 360;
x_diff = linspace(st.x2,st.x3,N_diff)';
A_diff = A_fun(x_diff);

Astar_d = m_dot*sqrt(T02)/(P02*mfpStar);
M_diff  = zeros(N_diff,1);
for k = 1:N_diff
    Ar = max(A_diff(k)/Astar_d,1.0000001);
    M_diff(k) = mach_from_area_ratio(Ar,'sub',gamma);
end
[T_diff,P_diff,rho_diff,u_diff,P0_diff,T0_diff] = static_from_total(M_diff,T02,P02,gamma,R);

fprintf('\n=== DIFUSOR INTERNO ===\n');
fprintf('  M(x2) = %.4f     M(x3) = %.4f\n',M_diff(1),M_diff(end));
fprintf('  P(x2) = %.2f kPa P(x3) = %.2f kPa\n',P_diff(1)/1e3,P_diff(end)/1e3);
fprintf('  T(x2) = %.2f K   T(x3) = %.2f K\n',T_diff(1),T_diff(end));

%% 8) CAMARA DE COMBUSTION x3 -> x4
% Transicion suave de T0, P0 y masa por adicion de combustible.
N_comb = 320;
x_comb = linspace(st.x3,st.x4,N_comb)';
s      = smooth01((x_comb-st.x3)/(st.x4-st.x3));

T0_comb = T02 + s*(T04-T02);
P0_comb = P02 + s*(P04-P02);
md_comb = m_dot.*(1 + p.f*s);
A_comb  = A_fun(x_comb);

M_comb = zeros(N_comb,1);
for k = 1:N_comb
    Astar_k = md_comb(k)*sqrt(T0_comb(k))/(P0_comb(k)*mfpStar);
    Ar      = max(A_comb(k)/Astar_k,1.0000001);
    M_comb(k) = mach_from_area_ratio(Ar,'sub',gamma);
end
[T_comb,P_comb,rho_comb,u_comb,P0_comb_out,T0_comb_out] = static_from_total(M_comb,T0_comb,P0_comb,gamma,R);

fprintf('\n=== CAMARA DE COMBUSTION ===\n');
fprintf('  T0 entrada = %.2f K       T0 salida = %.2f K\n',T02,T04);
fprintf('  P0 entrada = %.2f kPa     P0 salida = %.2f kPa\n',P02/1e3,P04/1e3);
fprintf('  M entrada  = %.4f         M salida  = %.4f\n',M_comb(1),M_comb(end));

%% 9) TOBERA C-D x4 -> x6
% No se integra con ode45. Se impone M=1 en garganta y se resuelve:
%   x4 -> x5: rama subsonica
%   x5 -> x6: rama supersonica
N_nozz1 = 220;
N_nozz2 = 320;
x_nozz1 = linspace(st.x4,st.x5,N_nozz1)';
x_nozz2 = linspace(st.x5,st.x6,N_nozz2)';
x_nozz  = [x_nozz1; x_nozz2(2:end)];
A_nozz  = A_fun(x_nozz);

M_nozz = zeros(size(x_nozz));
for k = 1:numel(x_nozz)
    Ar = max(A_nozz(k)/A5,1.0000001);
    if x_nozz(k) < st.x5 - 1e-10
        M_nozz(k) = mach_from_area_ratio(Ar,'sub',gamma);
    elseif abs(x_nozz(k)-st.x5) <= 1e-10
        M_nozz(k) = 1.0;
    else
        M_nozz(k) = mach_from_area_ratio(Ar,'sup',gamma);
    end
end
[T_nozz,P_nozz,rho_nozz,u_nozz,P0_nozz,T0_nozz] = static_from_total(M_nozz,T04,P04,gamma,R);

fprintf('\n=== TOBERA C-D ===\n');
fprintf('  M(x4) = %.4f     M(x5) = %.4f     M(x6) = %.4f\n',M_nozz(1),1.0,M_nozz(end));
fprintf('  P(x6)/Pa = %.4f\n',P_nozz(end)/Pa);

%% 10) UNIR RESULTADOS
x_t   = [x_diff;       x_comb(2:end);       x_nozz(2:end)];
M_t   = [M_diff;       M_comb(2:end);       M_nozz(2:end)];
T_t   = [T_diff;       T_comb(2:end);       T_nozz(2:end)];
P_t   = [P_diff;       P_comb(2:end);       P_nozz(2:end)];
rho_t = [rho_diff;     rho_comb(2:end);     rho_nozz(2:end)];
u_t   = [u_diff;       u_comb(2:end);       u_nozz(2:end)];
P0_t  = [P0_diff;      P0_comb_out(2:end);  P0_nozz(2:end)];
T0_t  = [T0_diff;      T0_comb_out(2:end);  T0_nozz(2:end)];
At    = A_fun(x_t);

m_ref = m_dot*ones(size(x_t));
idx_g = x_t >= st.x4;
m_ref(idx_g) = mg_dot;
m_chk = rho_t.*u_t.*At;
err_m = max(abs(m_chk - m_ref));

%% 11) EMPUJE Y PARAMETROS GLOBALES
u6  = u_t(end);
P6  = P_t(end);
A6  = At(end);
Fg  = mg_dot*u6 + (P6-Pa)*A6;
Fn  = Fg - m_dot*ua;
Isp = Fn/(mf_dot*9.80665);
Qin = mf_dot*p.LHV*p.eta_b;
eta_th = 0.5*max(mg_dot*u6^2 - m_dot*ua^2,0)/Qin;
eta_p  = 2*ua/(u6+ua);

fprintf('\n=== RESULTADOS GLOBALES ===\n');
fprintf('  M_exit       = %.4f\n',M_t(end));
fprintf('  T_exit       = %.2f K\n',T_t(end));
fprintf('  P_exit       = %.2f kPa\n',P_t(end)/1e3);
fprintf('  P_exit/Pa    = %.4f\n',P_t(end)/Pa);
fprintf('  u_exit       = %.2f m/s\n',u6);
fprintf('  Empuje bruto = %.2f N\n',Fg);
fprintf('  Empuje neto  = %.2f N\n',Fn);
fprintf('  Isp          = %.2f s\n',Isp);
fprintf('  eta_prop     = %.2f %%\n',eta_p*100);
fprintf('  eta_term     = %.2f %%\n',eta_th*100);
fprintf('  Error masa   = %.3e kg/s\n',err_m);

%% 12) GRAFICAS
plot_results(p,st,x,x_t,A,dAdx,re_plot,re_flow,ri,xlip,M_t,T_t,P_t,rho_t,u_t,P0_t,T0_t,m_chk,m_ref,Pa,rho_a,ua);

fprintf('\n=== Simulacion completada correctamente ===\n');

%% =========================================================
%% FUNCIONES LOCALES
%% =========================================================

function p = default_params()
% DEFAULT_PARAMS - Motor RAMJET de tesis, M_inf=2.0 a 10 km ISA

% Longitudes (m)
p.l1 = 0.20;
p.l2 = 0.22;
p.l3 = 0.32;
p.l4 = 0.38;
p.l5 = 0.14;
p.l6 = 0.24;

% Radios principales (m)
% rc se deja ligeramente mayor que en la version anterior para que:
% A(x3) > A(x2), es decir, el ducto x2->x3 funcione como difusor subsonico.
p.rc      = 0.090;   % radio camara, diametro 180 mm
p.rcd     = 0.046;   % radio garganta, diametro 92 mm
p.re_exit = 0.092;   % radio salida, diametro 184 mm

% Labio / entrada
p.xlip_frac = 0.22;
p.g_lip     = 0.024;
p.r_inlet   = 0.096;

% Spike
p.ri_x1   = 0.004;
p.ri_peak = 0.058;
p.xm_frac = 0.42;

% Discretizacion
p.N    = 2400;
p.gmin = 0.013;

% Termodinamica ISA 10 km
p.M_inf   = 2.0;
p.T_inf   = 223.15;
p.P_inf   = 26500;
p.R       = 287.05;
p.gamma   = 1.4;
p.Cp      = p.gamma*p.R/(p.gamma-1);
p.LHV     = 43.0e6;
p.f       = 0.030;
p.eta_d   = 0.92;  % recuperacion de presion total del inlet
p.eta_b   = 0.98;  % eficiencia de combustion / liberacion de calor
p.sigma_b = 0.95;  % relacion P0_salida/P0_entrada en camara
end

function [A, re_plot, ri, x, dAdx, st, re_flow, xlip] = ramjet_geometry(p)
% RAMJET_GEOMETRY - Geometria axisimetrica con A(x) suave.
% La continuidad se garantiza sobre el AREA, no solamente sobre los radios.

l1=p.l1; l2=p.l2; l3=p.l3; l4=p.l4; l5=p.l5; l6=p.l6;
x0=0; x1=l1; x2=l1+l2; x3=x2+l3; x4=x3+l4; x5=x4+l5; x6=x5+l6;
st = struct('x0',x0,'x1',x1,'x2',x2,'x3',x3,'x4',x4,'x5',x5,'x6',x6);

x    = linspace(x0,x6,p.N)';
xlip = x1 + p.xlip_frac*l2;
xm   = x2 + p.xm_frac*l3;
x3e  = x3 - 0.07*l3;

% Spike ri(x)
ri = zeros(size(x));
dridx = zeros(size(x));

idx = (x>=x1) & (x<=xm);
[ri(idx),dridx(idx)] = hd(x(idx),x1,p.ri_x1,0,xm,p.ri_peak,0);

idx = (x>xm) & (x<=x3e);
[ri(idx),dridx(idx)] = hd(x(idx),xm,p.ri_peak,0,x3e,0,0);

% Radio exterior visual antes de x2
re_plot = nan(size(x));

if xlip <= xm
    ri_xlip = hv(xlip,x1,p.ri_x1,0,xm,p.ri_peak,0);
else
    ri_xlip = hv(xlip,xm,p.ri_peak,0,x3e,0,0);
end
r_lip0 = min(ri_xlip + p.g_lip,0.87*p.r_inlet);

% Pendientes suaves del labio. Se fuerza pendiente cero en x2 para que la
% entrada del ducto no introduzca un pico artificial en dA/dx.
m_lip0 = (p.r_inlet-r_lip0)/(x2-xlip);
idx = (x>=xlip) & (x<=x2);
[re_plot(idx),~] = hd(x(idx),xlip,r_lip0,m_lip0,x2,p.r_inlet,0);

% Area de flujo desde x2
A    = nan(size(x));
dAdx = nan(size(x));

% Valor de ri en x2
ri_x2 = hv(x2,x1,p.ri_x1,0,xm,p.ri_peak,0);

A2 = pi*(p.r_inlet^2 - ri_x2^2);
A3 = pi*p.rc^2;
A4 = A3;
A5 = pi*p.rcd^2;
A6 = pi*p.re_exit^2;

% Difusor interno x2->x3: A aumenta suavemente
idx = (x>=x2) & (x<=x3);
[A(idx),dAdx(idx)] = hd(x(idx),x2,A2,0,x3,A3,0);

% Camara x3->x4: A constante
idx = (x>x3) & (x<=x4);
A(idx) = A4; dAdx(idx) = 0;

% Convergente x4->x5
idx = (x>x4) & (x<=x5);
[A(idx),dAdx(idx)] = hd(x(idx),x4,A4,0,x5,A5,0);

% Divergente x5->x6
idx = (x>x5) & (x<=x6);
[A(idx),dAdx(idx)] = hd(x(idx),x5,A5,0,x6,A6,0);

% Radio exterior de flujo, calculado desde A(x) y ri(x)
re_flow = nan(size(x));
idx = ~isnan(A);
re_flow(idx) = sqrt(A(idx)/pi + ri(idx).^2);

% Para graficar: antes de x2 se usa el labio, despues x2 se usa re_flow
re_plot(x>=x2) = re_flow(x>=x2);

% Verificaciones
idx_d = (x>=x2) & (x<=x3);
gap_min = min(re_flow(idx_d)-ri(idx_d));
if gap_min < p.gmin
    warning('Gap minimo = %.1f mm < gmin = %.1f mm.',gap_min*1e3,p.gmin*1e3);
end

fprintf('\n=== GEOMETRIA ===\n');
fprintf('  x0=%.3f x1=%.3f x2=%.3f x3=%.3f x4=%.3f x5=%.3f x6=%.3f m\n',x0,x1,x2,x3,x4,x5,x6);
fprintf('  Diametro max coraza : %.1f mm\n',2*max(re_flow(~isnan(re_flow)))*1e3);
fprintf('  Diametro spike max  : %.1f mm\n',2*p.ri_peak*1e3);
fprintf('  Diametro camara     : %.1f mm\n',2*p.rc*1e3);
fprintf('  Diametro garganta   : %.1f mm\n',2*p.rcd*1e3);
fprintf('  Diametro salida     : %.1f mm\n',2*p.re_exit*1e3);
fprintf('  Gap en x2           : %.1f mm\n',(p.r_inlet-ri_x2)*1e3);
fprintf('  Gap minimo difusor  : %.1f mm\n',gap_min*1e3);
fprintf('  A(x2)=%.6f  A(x3)=%.6f  A(x5)=%.6f  A(x6)=%.6f m2\n',A2,A3,A5,A6);
fprintf('  dA/dx max abs       : %.6f m2/m\n',max(abs(dAdx(~isnan(dAdx)))));
end

function [T,P,rho,u,P0v,T0v] = static_from_total(M,T0,P0,gamma,R)
a = (gamma-1)/2;
T = T0 ./ (1 + a.*M.^2);
P = P0 ./ (1 + a.*M.^2).^(gamma/(gamma-1));
rho = P./(R*T);
u = M.*sqrt(gamma*R.*T);
P0v = P0 + zeros(size(M));
T0v = T0 + zeros(size(M));
end

function q = mass_flow_parameter(M,gamma,R)
q = sqrt(gamma/R).*M.*(1+(gamma-1)/2.*M.^2).^(-(gamma+1)/(2*(gamma-1)));
end

function M = mach_from_area_ratio(Ar,branch,gamma)
% Soluciona A/A* = f(M) por biseccion, evitando fzero y problemas de toolbox.
if Ar <= 1+1e-9
    M = 1.0;
    return;
end

if strcmpi(branch,'sub')
    lo = 1e-8; hi = 1-1e-8;
else
    lo = 1+1e-8; hi = 20;
    while area_mach(hi,gamma) < Ar
        hi = hi*1.5;
        if hi > 80
            error('No se pudo acotar la rama supersonica para A/A* = %.4f.',Ar);
        end
    end
end

for it = 1:100
    mid = 0.5*(lo+hi);
    fmid = area_mach(mid,gamma) - Ar;
    if strcmpi(branch,'sub')
        % En rama subsonica area_mach decrece de infinito a 1
        if fmid > 0
            lo = mid;
        else
            hi = mid;
        end
    else
        % En rama supersonica area_mach crece de 1 a infinito
        if fmid < 0
            lo = mid;
        else
            hi = mid;
        end
    end
end
M = 0.5*(lo+hi);
end

function Ar = area_mach(M,gamma)
Ar = (1./M) .* ((2/(gamma+1)) .* (1+(gamma-1)/2.*M.^2)).^((gamma+1)/(2*(gamma-1)));
end

function y = smooth01(t)
t = min(max(t,0),1);
y = t.^2.*(3 - 2*t);
end

function y = hv(x,x0,y0,m0,x1,y1,m1)
L=x1-x0; t=(x-x0)./L;
y=(2*t.^3-3*t.^2+1)*y0 + (t.^3-2*t.^2+t)*L*m0 + ...
  (-2*t.^3+3*t.^2)*y1 + (t.^3-t.^2)*L*m1;
end

function [y,dy] = hd(x,x0,y0,m0,x1,y1,m1)
L=x1-x0; t=(x-x0)./L;
y =(2*t.^3-3*t.^2+1)*y0 + (t.^3-2*t.^2+t)*L*m0 + ...
   (-2*t.^3+3*t.^2)*y1 + (t.^3-t.^2)*L*m1;
dy=((6*t.^2-6*t)*y0 + (3*t.^2-4*t+1)*L*m0 + ...
    (-6*t.^2+6*t)*y1 + (3*t.^2-2*t)*L*m1)./L;
end

function plot_results(p,st,x,x_t,A,dAdx,re_plot,re_flow,ri,xlip,M_t,T_t,P_t,rho_t,u_t,P0_t,T0_t,m_chk,m_ref,Pa,rho_a,ua)
cB=[0 0.45 0.74]; cR=[0.85 0.1 0.1]; cG=[0 0.55 0.2]; cM=[0.7 0.1 0.7]; cO=[0.85 0.45 0];
Xst=[st.x0,st.x1,st.x2,st.x3,st.x4,st.x5,st.x6];
lb={'x_0','x_1','x_2','x_3','x_4','x_5','x_6'};
ymx=max(re_flow(~isnan(re_flow)))*1.3;

%% Geometria
figure('Name','Geometria RAMJET','NumberTitle','off','Position',[30 470 1050 360]); hold on;
plot(x,re_plot,'k','LineWidth',2.5);
plot(x,-re_plot,'k','LineWidth',2.5);
idx_sp = ri > 1e-5;
fill([x(idx_sp); flipud(x(idx_sp))],[ri(idx_sp); -flipud(ri(idx_sp))],...
     [0.35 0.35 0.35],'EdgeColor','k','LineWidth',1.3);
plot([x(1) x(end)],[0 0],'k:','LineWidth',0.8);
for k=1:numel(Xst)
    xline(Xst(k),'b:','LineWidth',0.9);
    text(Xst(k),ymx*1.09,lb{k},'Color','b','FontSize',9,'HorizontalAlignment','center','FontWeight','bold');
end
xline(xlip,'r--','LineWidth',1.4);
text(xlip,-ymx*0.68,'x_{lip}','Color','r','FontSize',10,'HorizontalAlignment','center');
text((st.x2+st.x3)/2,ymx*1.23,'Difusor','Color',cG,'FontSize',12,'FontWeight','bold','HorizontalAlignment','center');
text((st.x3+st.x4)/2,ymx*1.23,'Camara','Color',cR,'FontSize',12,'FontWeight','bold','HorizontalAlignment','center');
text((st.x4+st.x6)/2,ymx*1.23,'Tobera C-D','Color',cB,'FontSize',12,'FontWeight','bold','HorizontalAlignment','center');
ri_x2 = interp1(x,ri,st.x2,'pchip');
re_x2 = interp1(x,re_flow,st.x2,'pchip');
plot([st.x2 st.x2],[ri_x2 re_x2],'k-','LineWidth',1.2);
text(st.x2+0.012,(ri_x2+re_x2)/2,sprintf('%.0f mm',(re_x2-ri_x2)*1e3),'FontSize',9,'Color',[0.2 0.2 0.2]);
axis equal; grid on;
xlim([x(1)-0.02,x(end)+0.02]); ylim([-ymx*1.45,ymx*1.62]);
xlabel('x (m)'); ylabel('radio (m)'); title('Geometria Parametrizable del Motor RAMJET'); hold off;

%% Geometria numerica: A y dA/dx
figure('Name','Area y dAdx','NumberTitle','off','Position',[30 70 1050 360]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
idv = ~isnan(A);
plot(x(idv),A(idv)*1e4,'Color',cB,'LineWidth',2.2);
for k=1:numel(Xst), xline(Xst(k),'k:','LineWidth',0.7); end
grid on; xlabel('x (m)'); ylabel('A (cm^2)'); title('Area de flujo A(x)');

nexttile; hold on;
idv = ~isnan(dAdx);
xv=x(idv); dAv=dAdx(idv);
yhi=max(dAv)*1.25; ylo=min(dAv)*1.25;
if yhi<=0, yhi=0.02; end
if ylo>=0, ylo=-0.02; end
patch([st.x2 st.x3 st.x3 st.x2],[ylo ylo yhi yhi],[0.82 0.90 1.00],'EdgeColor','none','FaceAlpha',0.40);
patch([st.x3 st.x4 st.x4 st.x3],[ylo ylo yhi yhi],[1.00 0.88 0.88],'EdgeColor','none','FaceAlpha',0.40);
patch([st.x4 st.x6 st.x6 st.x4],[ylo ylo yhi yhi],[0.88 1.00 0.88],'EdgeColor','none','FaceAlpha',0.40);
plot(xv,dAv,'Color',cR,'LineWidth',2.2);
yline(0,'k--','LineWidth',1.1);
for k=1:numel(Xst), xline(Xst(k),'k:','LineWidth',0.7); end
text((st.x2+st.x3)/2,yhi*0.80,{'Difusor','dA/dx > 0'},'FontSize',9,'HorizontalAlignment','center','Color',cB,'FontWeight','bold');
text((st.x3+st.x4)/2,yhi*0.80,{'Camara','dA/dx = 0'},'FontSize',9,'HorizontalAlignment','center','Color',cR,'FontWeight','bold');
text((st.x4+st.x6)/2,yhi*0.80,{'Tobera','C-D'},'FontSize',9,'HorizontalAlignment','center','Color',cG,'FontWeight','bold');
grid on; xlabel('x (m)'); ylabel('dA/dx (m^2/m)'); title('Derivada analitica continua dA/dx');
ylim([ylo,yhi]); xlim([x(1),x(end)]);

%% Termodinamica
figure('Name','Parametros termodinamicos RAMJET','NumberTitle','off','Position',[80 80 1180 720]);
tiledlayout(3,2,'TileSpacing','compact','Padding','compact');

nexttile; hold on;
plot(x_t,M_t,'k','LineWidth',2.0); yline(1,'r--','LineWidth',1.1);
add_stations(st); grid on; xlabel('x (m)'); ylabel('M'); title('Mach M(x)');

nexttile; hold on;
plot(x_t,T_t,'Color',cR,'LineWidth',2.0);
add_stations(st); grid on; xlabel('x (m)'); ylabel('T (K)'); title('Temperatura estatica T(x)');

nexttile; hold on;
plot(x_t,P_t/1e3,'Color',cB,'LineWidth',2.0); yline(Pa/1e3,'k:','LineWidth',1.1);
add_stations(st); grid on; xlabel('x (m)'); ylabel('P (kPa)'); title('Presion estatica P(x)');

nexttile; hold on;
plot(x_t,rho_t,'Color',cM,'LineWidth',2.0); yline(rho_a,'k:','LineWidth',1.1);
add_stations(st); grid on; xlabel('x (m)'); ylabel('\rho (kg/m^3)'); title('Densidad \rho(x)');

nexttile; hold on;
plot(x_t,u_t,'Color',cG,'LineWidth',2.0); yline(ua,'k:','LineWidth',1.1);
add_stations(st); grid on; xlabel('x (m)'); ylabel('u (m/s)'); title('Velocidad u(x)');

nexttile; hold on;
plot(x_t,P0_t/1e3,'Color',cO,'LineWidth',2.0);
add_stations(st); grid on; xlabel('x (m)'); ylabel('P_0 (kPa)'); title('Presion total P_0(x)');

%% Conservacion de masa y T0
figure('Name','Verificaciones','NumberTitle','off','Position',[260 130 900 330]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
plot(x_t,m_chk,'k','LineWidth',2.0);
plot(x_t,m_ref,'r--','LineWidth',1.4);
add_stations(st); grid on; xlabel('x (m)'); ylabel('\dot{m} (kg/s)'); title('Conservacion de masa');
legend('\rho u A','referencia','Location','best');

nexttile; hold on;
plot(x_t,T0_t,'Color',cO,'LineWidth',2.0);
add_stations(st); grid on; xlabel('x (m)'); ylabel('T_0 (K)'); title('Temperatura total T_0(x)');
end

function add_stations(st)
Xst=[st.x2,st.x3,st.x4,st.x5,st.x6];
for kk=1:numel(Xst)
    xline(Xst(kk),'k:','LineWidth',0.7);
end
end
