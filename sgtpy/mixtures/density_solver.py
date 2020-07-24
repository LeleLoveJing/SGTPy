import numpy as np
from scipy.optimize import minimize_scalar, brentq
from ..constants import kb, Na

def dPsaft_fun(rho, x, T, saft):
    rhomolecular = Na * rho 
    _, dafcn, d2afcn = saft.d2afcn_drho(x, rhomolecular, T)
    dPsaft = 2 * rhomolecular * dafcn + rhomolecular**2 * d2afcn
    #dPsaft /= Na
    return dPsaft

def Psaft_obj(rho, x, T, saft, Pspec):
    rhomolecular = Na * rho
    _, dafcn = saft.dafcn_drho(x, rhomolecular, T)
    Psaft = rhomolecular**2 * dafcn / Na
    return Psaft - Pspec

def density_topliss(state, x, T, P, saft):
    
    #lower boundary a zero density
    rho_lb = 1e-5
    #P_lb = 0.
    dP_lb = Na * kb * T
    
    #upper boundary limit at infinity pressure
    etamax = 0.7405
    #rho_lim = np.dot(x, (6 * etamax) / (saft.ms * np.pi * saft.sigma**3)) / Na
    rho_lim =  (6 * etamax) / np.dot(x, (saft.ms * np.pi * saft.sigma**3)) / Na
    #Mejorar esta parte con el maximo valor posible de eta de la densidad
    ub_sucess = False
    rho_ub = 0.4 *  rho_lim
    it = 0
    while not ub_sucess and it < 5:
        it += 1
        P_ub, dP_ub = saft.dP_drho(x, rho_ub, T)
        rho_ub += 0.1 *  rho_lim
        ub_sucess = P_ub > P and dP_ub > 0
    
    #Calculo de derivada numerica en densidad nula
    rho_lb1 = 1e-4 * rho_lim
    #rho_lb1 = 1e-5
    P_lb1, dP_lb1 = saft.dP_drho(x, rho_lb1, T)
    d2P_lb1 = (dP_lb1 - dP_lb) / rho_lb1
    if d2P_lb1 > 0:
        flag = 3
    else:
        flag = 1

    #Comienza Etapa 1
    bracket = [rho_lb, rho_ub]
    if flag == 1:
        #Se debe encontrar el punto de inflexion
        sol_inf = minimize_scalar(dPsaft_fun, args = (x, T, saft),
                                  bounds = bracket, method = 'Bounded' )
        rho_inf = sol_inf.x
        dP_inf = sol_inf.fun
        if dP_inf > 0:
            flag = 3
        else:
            flag = 2

    #Etapa 2
    if flag == 2:
        if state == 'L':
            bracket[0] = rho_inf
        elif state == 'V':
            bracket[1] = rho_inf
        rho_ext = brentq(dPsaft_fun, bracket[0], bracket[1], args =(x, T, saft))
        P_ext, dP_ext = saft.dP_drho(x, rho_ext, T)
        if P_ext > P and state == 'V':
            bracket[1] = rho_ext
        elif P_ext < P and state == 'L':
            bracket[0] = rho_ext
        else:
            flag = -1

    if flag == -1:
        rho = np.nan
    else:
        rho = brentq(Psaft_obj, bracket[0], bracket[1], args = (x, T, saft, P))

    return rho


def density_newton(rho0, x, T, P, saft):
    
    rho = 1.*rho0
    Psaft, dPsaft = saft.dP_drho(x, rho, T)
    FO = Psaft - P
    dFO = dPsaft
    for i in range(30):
        rho -= FO/dFO
        Psaft, dPsaft = saft.dP_drho(x, rho, T)
        FO = Psaft - P
        dFO = dPsaft
        if np.abs(FO) < 1e-10:
            break
    return rho
