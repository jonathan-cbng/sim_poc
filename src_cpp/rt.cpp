#include "rt.hpp"
#include "node.hpp"
#include <string>

RT::RT (int id_) : Node (id_), ap (nullptr) {}

std::string
RT::repr () const
{
  return "RT(" + std::to_string (id) + ")";
}
