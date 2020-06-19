
#define _CLC_ANY_DECL(TYPE) _CLC_OVERLOAD _CLC_DECL int any(TYPE v);

#define _CLC_VECTOR_ANY_DECL(TYPE) \
  _CLC_ANY_DECL(TYPE)              \
  _CLC_ANY_DECL(TYPE##2)           \
  _CLC_ANY_DECL(TYPE##3)           \
  _CLC_ANY_DECL(TYPE##4)           \
  _CLC_ANY_DECL(TYPE##8)           \
  _CLC_ANY_DECL(TYPE##16)

_CLC_VECTOR_ANY_DECL(char)
_CLC_VECTOR_ANY_DECL(short)
_CLC_VECTOR_ANY_DECL(int)
_CLC_VECTOR_ANY_DECL(long)
