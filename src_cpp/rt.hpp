#pragma once
#include "node.hpp"
#include <memory>
#include <string>

class AP;

class RT : public Node
{
public:
  std::shared_ptr<AP> ap;

  explicit RT (int id_ = -1);

  std::string repr () const;
};
