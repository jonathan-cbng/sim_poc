#pragma once
#include "node.hpp"
#include <memory>
#include <string>

class AP;

class RT : public Node
{
public:
  std::shared_ptr<AP> ap;

  explicit RT (int id = INVALID_ID);

  std::string repr () const;
};
