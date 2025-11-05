URL: https://dadosabertos.camara.leg.br/api/v2/

Endpoint deputados: /deputados?ordem=ASC&ordenarPor=nome
Resultado: 
{
  "dados": [
    {
      "email": "string",
      "id": 0,
      "idLegislatura": 0,
      "nome": "string",
      "siglaPartido": "string",
      "siglaUf": "string",
      "uri": "string",
      "uriPartido": "string",
      "urlFoto": "string"
    }
  ],
  "links": [
    {
      "href": "string",
      "rel": "string",
      "type": "string"
    }
  ]
}



Endpoint por deputado: /deputados/{id}
Resultado:
{
  "dados": {
    "cpf": "string",
    "dataFalecimento": "string",
    "dataNascimento": "string",
    "escolaridade": "string",
    "id": 0,
    "municipioNascimento": "string",
    "nomeCivil": "string",
    "redeSocial": [
      "string"
    ],
    "sexo": "string",
    "ufNascimento": "string",
    "ultimoStatus": {
      "condicaoEleitoral": "string",
      "data": "string",
      "descricaoStatus": "string",
      "email": "string",
      "gabinete": {
        "andar": "string",
        "email": "string",
        "nome": "string",
 "predio": "string",
        "sala": "string",
        "telefone": "string"
      },
      "id": 0,
      "idLegislatura": 0,
      "nome": "string",
      "nomeEleitoral": "string",
      "siglaPartido": "string",
      "siglaUf": "string",
      "situacao": "string",
      "uri": "string",
      "uriPartido": "string",
      "urlFoto": "string"
    },
    "uri": "string",
    "urlWebsite": "string"
  },
  "links": [
    {
      "href": "string",
      "rel": "string",
"type": "string"
    }
  ]
}


Endpoint por deputado - discurso : /deputados/{id}/discursos
Resultado:
{
  "dados": [
    {
      "dataHoraFim": "string",
      "dataHoraInicio": "string",
      "faseEvento": {
        "dataHoraFim": "string",
        "dataHoraInicio": "string",
        "titulo": "string"
      },
      "keywords": "string",
      "sumario": "string",
      "tipoDiscurso": "string",
      "transcricao": "string",
      "uriEvento": "string",
      "urlAudio": "string",
      "urlTexto": "string",
      "urlVideo": "string"
    }
  ],
"links": [
    {
      "href": "string",
      "rel": "string",
      "type": "string"
    }
  ]
}
