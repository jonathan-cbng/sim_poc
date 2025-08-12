#include "node.hpp"
#include <random>

Node::Node (int id_)
{
  if (id_ == -1)
    {
      static std::random_device rd;
      static std::mt19937 gen (rd ());
      static std::uniform_int_distribution<> dis (1, 1000000);
      id = dis (gen);
    }
  else
    {
      id = id_;
    }
}

std::string
Node::repr () const
{
  return "Node(" + std::to_string (id) + ")";
}
