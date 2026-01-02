from backend.core.database import mongodb

class ListingRepository:
    async def get_categories(self):
        return await mongodb.db.categories.find({}, {"_id": 0}).to_list(100)
    
    async def get_category_by_id(self, id, data_filter=None):
        projection = {"_id": 0}
        if data_filter:
            projection.update(data_filter)
        return await mongodb.db.categories.find_one(id, projection).to_list(100)
        
    
    async def update_listing(self, listing_id, batch_id=None, data=None, new_data=None, delete_option=None, inc_data=None):
        query={"id": listing_id}
        update_query = {}
        if batch_id:
            query["batches.id"] = batch_id
        
        if data:
            update_query["$set"] =  data
        if new_data:
            update_query["$push"] =  new_data
        if delete_option:
            update_query["$pull"] =  delete_option
        if inc_data:
            update_query["$inc"] = inc_data


        if not update_query:
            return False
        
        return await mongodb.db.listing.update_one(query, update_query)
    
    async def get_listing_by_id(self, listing_id, data_filter=None):
        projection = {"_id": 0}
        if data_filter:
            projection.update(data_filter)
        return await mongodb.db.listings.find_one({"id": listing_id}, projection)
    
    
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
    
