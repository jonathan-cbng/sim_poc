#include "ap.hpp"

AP::AP (int id_) : Node (id_) {}

void
AP::add_rt (std::shared_ptr<RT> rt)
{
  rts.insert (rt);
  rt->ap = std::shared_ptr<AP> (this, [] (AP *) {});
}

void
AP::remove_rt (std::shared_ptr<RT> rt)
{
  rts.erase (rt);
  rt->ap = nullptr;
}

std::string
AP::repr () const
{
  return "AP(" + std::to_string (id) + ")";
}
