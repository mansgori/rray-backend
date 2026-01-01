from backend.core.database import mongodb

class ListingRepository:
    async def get_categories(self):
        return await mongodb.db.categories.find({}, {"_id": 0}).to_list(100)
    
    async def get_category_by_id(self, id, data_filter=None):
        projection = {"_id": 0}
        if data_filter:
            projection.update(data_filter)
        return await mongodb.db.categories.find_one(id, projection).to_list(100)
        
    
    async def get_listing_by_id(self, listing_id):
        return await mongodb.db.listings.find_onefind_one({"id": listing_id}, {"_id": 0})
    
    async def search_pipeline(
        self, city, age, category,
        is_online, trial,
        skip, limit
    ):
        pipeline = []

        pipeline.append({
            "$match": {
                "status": "active",
                "approval_status": "approved",
                "is_live": True
            }
        })

        if age:
            pipeline.append({
                "$match": {
                    "age_min": {"$lte": age},
                    "age_max": {"$gte": age}
                }
            })
        
        if category:
            pipeline.append({"$match": {"category": category}})

        if is_online is not None:
            pipeline.append({"$match": {"is_online": is_online}})

        if trial:
            pipeline.append({"$match": {"trial_available": True}})

        pipeline.append({
            "$sort": {
                "trial_available": -1,
                "rating": -1
            }
        })

        pipeline.extend([
            {"$skip": skip},
            {"$limit": limit}
        ])

        pipeline.append({
            "$lookup": {
                "from": "partners",
                "localField": "partner_id",
                "foreignField": "id",
                "as": "partner_data"
            }
        })

        pipeline.append({
            "$lookup": {
                "from": "venues",
                "localField": "venue_id",
                "foreignField": "id",
                "as": "venue_data"
            }
        })

        return await mongodb.db.listings.aggregate(pipeline).to_list(None)