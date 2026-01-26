def gerar_dxf_mesa(filename="mesa_organica.dxf"):
    def bezier(p0, p1, p2, p3, n=30):
        pts = []
        for i in range(n + 1):
            t = i / n
            x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
            y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
            pts.append((x, y))
        return pts

    # Definição dos pontos conforme sua geometria
    c1 = bezier([150, 1000], [600, 1050], [1200, 1000], [1800, 800])
    c2 = bezier([1800, 800], [1900, 600], [1900, 200], [1800, 0])
    c3 = bezier([1800, 0], [1200, -50], [600, -20], [150, 0])
    c4 = bezier([150, 0], [30, 200], [30, 800], [150, 1000])
    
    pontos = c1 + c2[1:] + c3[1:] + c4[1:-1]

    # Escrita do arquivo DXF puro
    with open(filename, 'w') as f:
        f.write("0\nSECTION\n2\nENTITIES\n")
        f.write("0\nLWPOLYLINE\n100\nAcDbEntity\n8\n0\n100\nAcDbPolyline\n")
        f.write(f"90\n{len(pontos)}\n70\n1\n") # 70\n1 significa polilinha fechada
        for x, y in pontos:
            f.write(f"10\n{x:.3f}\n20\n{y:.3f}\n")
        f.write("0\nENDSEC\n0\nEOF\n")
    
    print(f"Arquivo {filename} criado com sucesso!")

gerar_dxf_mesa()
