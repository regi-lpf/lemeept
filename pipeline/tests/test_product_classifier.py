from pipeline.product_classifier import classificar_tipo_produto
from pipeline.data_model import TipoProduto

# Casos básicos
assert classificar_tipo_produto("Desenvolvimento de uma sequência didática para EPT")[0] == TipoProduto.MATERIAL_DIDATICO
assert classificar_tipo_produto("Oficinas pedagógicas sobre memórias")[0] == TipoProduto.CURSO_OFICINA
assert classificar_tipo_produto("Aplicativo móvel para gestão escolar")[0] == TipoProduto.SOFTWARE_APLICATIVO

# Borda
assert classificar_tipo_produto("")[0] == TipoProduto.PENDENTE_REVISAO
assert classificar_tipo_produto(None)[0] == TipoProduto.PENDENTE_REVISAO if hasattr(classificar_tipo_produto, "__call__") else True

print("Classificador validado!")
