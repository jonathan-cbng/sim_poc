#include "node.hpp"
#include <random>
#include <string>

Node::Node (int id)
{
  if (id == INVALID_ID)
    {
      static std::random_device rd;
      static std::mt19937 gen (rd ());
      static std::uniform_int_distribution<> dis (1, MAX_ID);
      this->id = dis (gen);
    }
  else
    {
      this->id = id;
    }
}

std::string
Node::repr () const
{
  return "Node(" + std::to_string (id) + ")";
}
