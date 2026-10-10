"""UFs, regiões e a malha do mapa."""


REGIONS = {1: "Norte", 2: "Nordeste", 3: "Sudeste", 4: "Sul", 5: "Centro-Oeste"}

# cod IBGE, sigla, nome
UFS = (
    (11, "RO", "Rondônia"), (12, "AC", "Acre"), (13, "AM", "Amazonas"),
    (14, "RR", "Roraima"), (15, "PA", "Pará"), (16, "AP", "Amapá"),
    (17, "TO", "Tocantins"), (21, "MA", "Maranhão"), (22, "PI", "Piauí"),
    (23, "CE", "Ceará"), (24, "RN", "Rio Grande do Norte"), (25, "PB", "Paraíba"),
    (26, "PE", "Pernambuco"), (27, "AL", "Alagoas"), (28, "SE", "Sergipe"),
    (29, "BA", "Bahia"), (31, "MG", "Minas Gerais"), (32, "ES", "Espírito Santo"),
    (33, "RJ", "Rio de Janeiro"), (35, "SP", "São Paulo"), (41, "PR", "Paraná"),
    (42, "SC", "Santa Catarina"), (43, "RS", "Rio Grande do Sul"),
    (50, "MS", "Mato Grosso do Sul"), (51, "MT", "Mato Grosso"), (52, "GO", "Goiás"),
    (53, "DF", "Distrito Federal"),
)
UF_BY_SIGLA = {sigla: cod for cod, sigla, _ in UFS}
UF_NAME = {cod: nome for cod, _, nome in UFS}
UF_SIGLA = {cod: sigla for cod, sigla, _ in UFS}


def region_of(cod_uf: int) -> int:
    return cod_uf // 10


def _signed_area(ring) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))


def rewind_for_d3(geojson: dict) -> dict:
    """Plotly (d3-geo) quer anel externo horário; o IBGE entrega anti-horário
    (padrão RFC 7946), o que faz o polígono "inverter" e pintar o mundo todo."""
    def fix(polygon):
        return [ring if (_signed_area(ring) < 0) == (i == 0) else ring[::-1]
                for i, ring in enumerate(polygon)]

    for feature in geojson["features"]:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            geom["coordinates"] = fix(geom["coordinates"])
        elif geom["type"] == "MultiPolygon":
            geom["coordinates"] = [fix(poly) for poly in geom["coordinates"]]
    return geojson
